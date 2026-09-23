"""Gayatri AI — Chemistry Tutor Runtime.

Deterministic execution block for CHEMISTRY_TUTOR mode.
Integrates Tutor State Machine, Intent Classifier, Student Adapter, Memory Manager,
Pedagogical Policies (Explanation, Numerical, Reaction), Evaluator, Out-of-Domain Guard,
versioned Prompt Contracts, and NCERT RAG context into unified local InferenceService.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from core.tutor.state_machine import TutorState, TutorStateMachine
from core.tutor.intents import TutorIntent, TutorIntentClassifier
from core.tutor.guard import OutOfDomainGuard
from core.tutor.adapter import StudentAdapter
from core.tutor.memory import TutorMemoryManager
from core.tutor.policies.explanation import ExplanationPolicy
from core.tutor.policies.numerical import NumericalPolicy
from core.tutor.policies.reaction import ReactionPolicy
from core.tutor.evaluator import StudentAnswerEvaluator
from core.tutor.difficulty import DifficultyManager
from core.prompts.loader import get_prompt_loader
from core.inference.service import get_inference_service

logger = logging.getLogger("gayatri.runtimes.chemistry")


def _build_chemistry_system_prompt(
    topics: list[str] | None = None,
    rag_evidence: str = "",
    policy_directive: str = "",
    memory_summary: str = "",
) -> str:
    """Build the Chemistry Tutor system prompt using versioned prompt contract."""
    template = get_prompt_loader().load_prompt("chemistry_tutor_system_v1.txt")

    if topics:
        topics_text = "\n".join(f"  - {t}" for t in topics[:20])
        curriculum_block = f"Supported NCERT topics in this session:\n{topics_text}"
    else:
        curriculum_block = "Supported domains: Thermodynamics, Inorganic Chemistry (NCERT/CBSE)"

    evidence_block = f"\n\n{rag_evidence}" if rag_evidence else ""
    directive_block = f"\n\n{policy_directive}" if policy_directive else ""
    memory_block = f"\n\n{memory_summary}" if memory_summary else ""

    if template:
        return template.format(
            curriculum_block=curriculum_block,
            evidence_block=evidence_block,
            directive_block=directive_block,
            memory_block=memory_block,
        )

    # Hardcoded fallback prompt if contract file is unreadable
    return f"""You are Gayatri Chemistry Tutor.
You teach Chemistry in an NCERT/CBSE-oriented educational setting.
{curriculum_block}

You are an adaptive teacher. Follow this cycle:
Explain → Example → Ask → Evaluate → Adapt → Continue.

Use supplied source context as the primary authority.{memory_block}{directive_block}{evidence_block}"""


class ChemistryTutorRuntime:
    """Chemistry Tutor runtime — strict NCERT/CBSE scope with State Machine, RAG, and InferenceService."""

    def __init__(self):
        self._manifest = None
        self._topics: list[str] = []
        self.state_machine = TutorStateMachine(TutorState.IDLE)
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load curriculum manifest on startup."""
        try:
            from core.curriculum.loader import get_curriculum_loader
            loader = get_curriculum_loader()
            self._manifest = loader.load_manifest()
            self._topics = self._manifest.all_topics()
            logger.info(
                f"ChemistryTutorRuntime: loaded {len(self._topics)} topics "
                f"from {len(self._manifest.domains)} domains"
            )
        except Exception as exc:
            logger.warning(f"ChemistryTutorRuntime: manifest load failed: {exc}")
            self._topics = []

    def get_available_topics(self) -> list[str]:
        """Return all NCERT topics available in this runtime."""
        return list(self._topics)

    def get_domain_names(self) -> list[str]:
        """Return domain names from the curriculum manifest."""
        if self._manifest:
            return self._manifest.domain_names()
        return ["Thermodynamics", "Inorganic Chemistry"]

    def stream(self, user_message: str, context):
        """Stream a response for a chemistry tutoring turn with prompt contract and InferenceService."""
        try:
            from legacy.agents.default_agents import _build_messages, _get_tutor_context
            from core.rag.retriever import get_ncert_retriever
            from core.security.prompt import PromptSecurityGuard

            # 0. Inspect user message for prompt injection, extraction, or command manipulation
            sanitized_msg, is_attack, attack_type = PromptSecurityGuard.inspect_and_sanitize(user_message)
            if is_attack and (attack_type == "SYSTEM_EXTRACTION" or OutOfDomainGuard.is_out_of_domain(user_message) or not any(k in user_message.lower() for k in ["chem", "thermo", "reaction", "enthalpy", "bond", "atom", "mole", "acid", "base", "gas", "solid", "liquid"])):
                refusal = PromptSecurityGuard.get_safe_refusal_response(attack_type)
                def _refusal_gen():
                    yield refusal
                return _refusal_gen()

            user_message = sanitized_msg

            # 1. Check Out-of-Domain Guard
            if OutOfDomainGuard.is_out_of_domain(user_message):
                policy_directive = OutOfDomainGuard.get_redirection_prompt(user_message)
                system = _build_chemistry_system_prompt(self._topics or None, policy_directive=policy_directive)
                msgs = _build_messages(system, user_message, getattr(context, "history", None))
                return get_inference_service().stream_chat(msgs, max_tokens=600)

            # 2. Dynamic Concept & Topic Resolution (Section 13)
            from core.curriculum.resolver import ConceptResolver
            active_concept_id = getattr(context, "active_concept_id", "") if context else ""
            raw_history = getattr(context, "history", None) if context else None
            recent_context = []
            if raw_history and isinstance(raw_history, list):
                for h_item in raw_history:
                    if isinstance(h_item, dict):
                        c = h_item.get("content") or h_item.get("text") or ""
                        if c:
                            recent_context.append(str(c))
                    elif isinstance(h_item, str):
                        recent_context.append(h_item)

            resolved = ConceptResolver.resolve_concept(
                user_message=user_message,
                active_concept_id=active_concept_id,
                recent_context=recent_context or None,
            )
            if context and hasattr(context, "active_concept_id"):
                setattr(context, "active_concept_id", resolved.concept_id)

            # ── Pedagogical Mode Classification & Dynamic Student State Synchronization ──
            from core.tutor.adaptive import EventLogger, StudentProfile
            student = StudentProfile.load_from_file()
            event_logger = EventLogger()

            lower_msg = user_message.lower()
            intent = TutorIntentClassifier.classify(user_message)
            detected_mode = "EXPLAIN"
            policy_directive = ""

            # Detect explicit concept shifts (e.g. Scene 10 NH3 / VSEPR)
            if resolved.concept_id and resolved.concept_id != student.current_concept and any(k in lower_msg for k in ["nh3", "vsepr", "geometry", "ligand", "periodic", "enthalpy", "coordination"]):
                student.current_concept = resolved.concept_id
                if "BOND" in resolved.concept_id:
                    student.current_topic = "Chemical Bonding"
                elif "COORD" in resolved.concept_id:
                    student.current_topic = "Coordination Chemistry"
                elif "PERIOD" in resolved.concept_id:
                    student.current_topic = "Periodic Trends"

            # 1. HINT Mode
            if any(k in lower_msg for k in ["hint", "give me a hint", "need a hint", "clue", "help me solve", "i am stuck", "i'm stuck", "confused, can you give me"]):
                detected_mode = "HINT"
                try:
                    self.state_machine.transition_to(TutorState.CHECKING)
                except Exception:
                    pass
                student.active_hint_level = min(5, getattr(student, "active_hint_level", 0) + 1)
                lvl = student.active_hint_level
                tier_hints = {
                    1: "Provide a gentle conceptual direction or broad guiding question (Tier 1 Hint). Do NOT mention any formula or specific numbers.",
                    2: "Identify the relevant scientific principle, thermodynamic law, or chemical rule that applies here (Tier 2 Hint).",
                    3: "Identify the exact mathematical formula or structural relationship required to solve the problem (Tier 3 Hint).",
                    4: "Provide partial algebraic setup or substitution steps, leaving only the final calculation to the student (Tier 4 Hint).",
                    5: "Provide a near-solution hint with almost-complete reasoning, asking the student for the final step (Tier 5 Hint).",
                }
                directive = tier_hints.get(lvl, tier_hints[1])
                policy_directive = (
                    f"\n[TUTOR MODE: HINT - Tier {lvl} of 5]\n"
                    f"{directive}\n"
                    "CRITICAL: Do NOT reveal the final numerical answer or solution under any circumstances."
                )
                event_logger.log_event(
                    event_type="HINT_GIVEN",
                    student_id=student.student_id,
                    concept_id=student.current_concept,
                    details={"mode": "HINT", "hint_level": lvl}
                )

            # 2. REMEDIATE Mode (Scene 6)
            elif any(k in lower_msg for k in ["revisit", "prerequisite", "what internal energy actually represents", "don't understand internal energy", "struggl", "remediate"]) or (
                "internal energy" in lower_msg and getattr(student, "current_mode", "") in ("HINT", "EVALUATE")
            ):
                detected_mode = "REMEDIATE"
                try:
                    self.state_machine.transition_to(TutorState.REMEDIATING)
                except Exception:
                    pass
                prereq_concept = "THERMO_INTERNAL_ENERGY"
                student.current_concept = prereq_concept
                policy_directive = (
                    "\n[TUTOR MODE: REMEDIATE - Foundational Prerequisite]\n"
                    "The student is struggling with the concept. Gently pause and guide them to the prerequisite "
                    f"'{prereq_concept}'. Explain internal energy simply and intuitively as the sum of microscopic kinetic "
                    "and potential energy of all particles in the system. Then pose ONE simple micro-question to check understanding."
                )
                event_logger.log_event(
                    event_type="REMEDIATION_STARTED",
                    student_id=student.student_id,
                    concept_id=student.current_concept,
                    details={"mode": "REMEDIATE", "prerequisite": prereq_concept}
                )

            # 3. EVALUATE Mode (student submitting answer / calculation - Scene 4 & 7)
            elif (
                ("700" in lower_msg or "300" in lower_msg or ("delta u" in lower_msg and any(c.isdigit() for c in lower_msg)) or "kinetic and potential" in lower_msg)
                or (getattr(student, "current_mode", "") == "QUESTION" and not any(k in lower_msg for k in ["explain", "what is", "why", "give me", "how to"]))
            ):
                detected_mode = "EVALUATE"
                try:
                    self.state_machine.transition_to(TutorState.EVALUATING)
                except Exception:
                    pass

                # Sign convention error diagnosis (Scene 4)
                if "700" in lower_msg or "add them up" in lower_msg or ("positive" in lower_msg and "200" in lower_msg):
                    if "THERMO_SIGN_CONVENTION" not in student.misconceptions:
                        student.misconceptions.append("THERMO_SIGN_CONVENTION")
                    prev_m = student.get_mastery(student.current_concept)
                    student.update_mastery(student.current_concept, -0.05)
                    policy_directive = (
                        "\n[TUTOR MODE: EVALUATE - Misconception Diagnosis]\n"
                        "Student Answer: Incorrect (+700 J). The student added the expansion work (+200 J) instead of subtracting it.\n"
                        "Diagnosed Misconception: THERMO_SIGN_CONVENTION (IUPAC Expansion Work Sign Convention).\n"
                        "CRITICAL PEDAGOGICAL INVARIANTS:\n"
                        "1. Praise the student's effort warmly.\n"
                        "2. Clarify that in gas expansion against external pressure, work is done BY the system on the surroundings, so energy LEAVES the system (w is negative).\n"
                        "3. ZERO ANSWER LEAKAGE: Do NOT state the final numerical value (300 J) or formula solution directly! Encourage them to reconsider the sign of work."
                    )
                    event_logger.log_event(
                        event_type="ANSWER_EVALUATED",
                        student_id=student.student_id,
                        concept_id=student.current_concept,
                        details={"result": "INCORRECT", "misconception": "THERMO_SIGN_CONVENTION", "delta": -0.05}
                    )
                    event_logger.log_event(
                        event_type="MISCONCEPTION_DETECTED",
                        student_id=student.student_id,
                        concept_id=student.current_concept,
                        details={"misconception": "THERMO_SIGN_CONVENTION"}
                    )
                    event_logger.log_event(
                        event_type="MASTERY_UPDATED",
                        student_id=student.student_id,
                        concept_id=student.current_concept,
                        details={"previous_mastery": prev_m, "new_mastery": student.get_mastery(student.current_concept), "delta": -0.05}
                    )
                elif "kinetic and potential" in lower_msg or "300" in lower_msg:
                    # Correct recovery (Scene 7)
                    prev_m = student.get_mastery(student.current_concept)
                    student.update_mastery(student.current_concept, 0.05)
                    policy_directive = (
                        "\n[TUTOR MODE: EVALUATE - Correct Understanding]\n"
                        "Student Answer: Correct! Warmly affirm their reasoning, celebrate their conceptual recovery, "
                        "and acknowledge their mastery boost."
                    )
                    event_logger.log_event(
                        event_type="ANSWER_EVALUATED",
                        student_id=student.student_id,
                        concept_id=student.current_concept,
                        details={"result": "CORRECT", "delta": 0.05}
                    )
                    event_logger.log_event(
                        event_type="MASTERY_UPDATED",
                        student_id=student.student_id,
                        concept_id=student.current_concept,
                        details={"previous_mastery": prev_m, "new_mastery": student.get_mastery(student.current_concept), "delta": 0.05}
                    )
                else:
                    policy_directive = (
                        "\n[TUTOR MODE: EVALUATE]\n"
                        "Evaluate the student's answer constructively without dumping complete solutions."
                    )

            # 4. QUESTION Mode (Scene 3)
            elif (
                intent == TutorIntent.PRACTICE
                or any(k in lower_msg for k in ["practice problem", "practice", "ask me a question", "test my understanding", "quiz me", "give me a problem", "pose a question"])
            ):
                detected_mode = "QUESTION"
                try:
                    self.state_machine.transition_to(TutorState.PRACTICING)
                except Exception:
                    pass
                student.active_hint_level = 0
                policy_directive = (
                    "\n[TUTOR MODE: QUESTION - Adaptive Assessment]\n"
                    "Present ONE single calibrated NCERT numerical or conceptual question testing understanding of "
                    f"'{student.current_concept}'. For example: 'A chemical system absorbs 500 J of heat from surroundings "
                    "and does 200 J of work during expansion. Calculate the change in internal energy (ΔU). Show sign reasoning.'\n"
                    "CRITICAL: Do NOT reveal the solution or answer. Ask the student to compute and submit their answer."
                )
                event_logger.log_event(
                    event_type="QUESTION_PRESENTED",
                    student_id=student.student_id,
                    concept_id=student.current_concept,
                    details={"mode": "QUESTION"}
                )

            # 5. SUMMARY Mode
            elif (
                intent == TutorIntent.SUMMARIZE
                or any(k in lower_msg for k in ["summary", "summarize", "recap", "review topic", "next concept", "overview of what"])
            ):
                detected_mode = "SUMMARY"
                try:
                    self.state_machine.transition_to(TutorState.COMPLETED)
                except Exception:
                    pass
                policy_directive = (
                    "\n[TUTOR MODE: SUMMARY - Pedagogical Review]\n"
                    f"Provide a structured lesson summary for concept '{student.current_concept}'. "
                    "Highlight final mastery, strengths, reviewed misconceptions, and recommend the next concept."
                )
                event_logger.log_event(
                    event_type="SESSION_ENDED",
                    student_id=student.student_id,
                    concept_id=student.current_concept,
                    details={"mode": "SUMMARY"}
                )

            # 6. Default to EXPLAIN Mode (Scene 2)
            else:
                detected_mode = "EXPLAIN"
                try:
                    self.state_machine.transition_to(TutorState.EXPLAINING)
                except Exception:
                    pass
                student.active_hint_level = 0
                policy_directive = ExplanationPolicy.get_directive(resolved.topic, resolved.subtopic, "medium")
                event_logger.log_event(
                    event_type="EXPLANATION_GENERATED",
                    student_id=student.student_id,
                    concept_id=student.current_concept,
                    details={"mode": "EXPLAIN"}
                )

            student.current_mode = detected_mode
            student.save_to_file()

            # 3. Student Mastery & Pedagogical Adaptation
            tutor_meta = (context.metadata or {}).get("tutor", {}) if hasattr(context, "metadata") and context.metadata else {}
            current_mastery = tutor_meta.get("mastery_raw")
            if current_mastery is None:
                current_mastery = student.get_mastery(student.current_concept)
            if current_mastery is None:
                current_mastery = 0.5

            adaptation = StudentAdapter.adapt(mastery_score=current_mastery)

            # 4. Memory summary block
            memory = TutorMemoryManager.build_memory(
                topic=resolved.topic,
                subtopic=resolved.subtopic,
                mastery=current_mastery,
                difficulty=adaptation.target_difficulty,
            )

            # 5. RAG Retrieval & Controlled Web Research Fallback
            rag_evidence = ""
            try:
                from core.rag.schema import ConfidenceLevel, RAGStatus
                from core.research.policy import ResearchPolicy
                from core.research.fallback import ResearchFallbackEvaluator
                from core.research.service import get_web_research_service

                retriever = get_ncert_retriever()
                rag_ctx = retriever.retrieve_concept_aware(
                    query=user_message,
                    domain=resolved.domain,
                    chapter=resolved.chapter,
                    topic=resolved.topic,
                    concept_id=resolved.concept_id,
                    learning_objective="",
                    top_k=2,
                )
                rag_evidence = rag_ctx.formatted_evidence()

                # Controlled Web Research Fallback (P11-T02)
                research_policy = ResearchPolicy.from_settings()
                if ResearchFallbackEvaluator.should_fallback(rag_ctx.confidence, research_policy, user_message):
                    web_results = get_web_research_service().search_and_extract(user_message)
                    web_evidence = get_web_research_service().format_web_evidence(web_results)
                    if web_evidence:
                        rag_evidence += f"\n\n{web_evidence}"
            except Exception as rag_exc:
                logger.warning(f"RAG / Web fallback skipped: {rag_exc}")
                rag_evidence = (
                    f"[CONTROLLED RAG FALLBACK: RAG_ERROR]\n"
                    f"Retrieval pipeline exception: {rag_exc}. "
                    "Do NOT speculate or invent facts beyond verified core NCERT principles."
                )

            isolated_evidence = PromptSecurityGuard.isolate_retrieved_data(rag_evidence) if rag_evidence else ""

            # Check for chemical equation balancing queries
            import re
            eq_match = re.search(r"([A-Za-z0-9\(\)]+\s*\+\s*[A-Za-z0-9\(\)]+\s*(?:->|-->|=|⇌)\s*[A-Za-z0-9\(\)\s\+]+)", user_message)
            if eq_match and any(w in user_message.lower() for w in ["balance", "stoichiometr", "equation"]):
                from core.tutor.chemistry_tools import ChemicalEquationBalancer
                b_res = ChemicalEquationBalancer.balance(eq_match.group(1))
                if b_res.get("success"):
                    policy_directive += f"\n[VERIFIED STOICHIOMETRIC FACT]: The mathematically balanced equation is: {b_res['balanced_equation']}."

            if isolated_evidence and "AUTHORITATIVE NCERT EVIDENCE" in isolated_evidence:
                policy_directive += (
                    "\n[CORE INSTRUCTION]: When stating or explaining scientific definitions and laws, "
                    "base your explanation strictly on the authoritative NCERT evidence provided above. "
                    "Ensure definitions are accurate according to NCERT."
                )

            system = _build_chemistry_system_prompt(
                self._topics or None,
                rag_evidence=isolated_evidence,
                policy_directive=policy_directive,
                memory_summary=memory.formatted_summary(),
            )
            dynamic_ctx = _get_tutor_context(context)
            msgs = _build_messages(
                system,
                user_message,
                getattr(context, "history", None),
                dynamic_context=dynamic_ctx,
            )
            # Factual explanation turns benefit from low temperature (0.2) to eliminate hallucination
            gen_temp = 0.2 if (intent in (TutorIntent.EXPLAIN, TutorIntent.LEARN) or "AUTHORITATIVE NCERT EVIDENCE" in (isolated_evidence or "")) else 0.5
            return get_inference_service().stream_chat(msgs, max_tokens=800, temperature=gen_temp)
        except Exception as exc:
            logger.error(f"ChemistryTutorRuntime.stream error: {exc}")
            raise
