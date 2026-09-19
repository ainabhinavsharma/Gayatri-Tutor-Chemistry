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

            # 1. Check Out-of-Domain Guard
            if OutOfDomainGuard.is_out_of_domain(user_message):
                policy_directive = OutOfDomainGuard.get_redirection_prompt(user_message)
                system = _build_chemistry_system_prompt(self._topics or None, policy_directive=policy_directive)
                msgs = _build_messages(system, user_message, getattr(context, "history", None))
                return get_inference_service().stream_chat(msgs, max_tokens=600)

            # 2. Dynamic Concept & Topic Resolution (Phase 3 P3-T01 to P3-T04)
            from core.curriculum.resolver import ConceptResolver
            active_concept_id = getattr(context, "active_concept_id", "") if context else ""
            resolved = ConceptResolver.resolve_concept(user_message, active_concept_id=active_concept_id)
            if context and hasattr(context, "active_concept_id"):
                setattr(context, "active_concept_id", resolved.concept_id)

            # Intent Classification & State Machine Transition
            intent = TutorIntentClassifier.classify(user_message)
            if intent == TutorIntent.SOLVE:
                self.state_machine.transition_to(TutorState.EXPLAINING)
                policy_directive = NumericalPolicy.get_directive()
            elif intent == TutorIntent.PRACTICE:
                self.state_machine.transition_to(TutorState.PRACTICING)
                policy_directive = NumericalPolicy.get_directive()
            elif intent in (TutorIntent.EXPLAIN, TutorIntent.LEARN):
                self.state_machine.transition_to(TutorState.EXPLAINING)
                policy_directive = ExplanationPolicy.get_directive(resolved.topic, resolved.subtopic, "medium")
            else:
                policy_directive = ExplanationPolicy.get_directive(resolved.topic, resolved.subtopic, "medium")

            # 3. Student Answer Evaluation if checking or evaluating
            eval_result = StudentAnswerEvaluator.evaluate(user_message)
            adaptation = StudentAdapter.adapt(mastery_score=eval_result.confidence)

            # 4. Memory summary block
            memory = TutorMemoryManager.build_memory(
                topic=resolved.topic,
                mastery=eval_result.confidence,
                difficulty=adaptation.target_difficulty,
            )

            # 5. RAG Retrieval & Controlled Web Research Fallback
            rag_evidence = ""
            try:
                from core.rag.schema import ConfidenceLevel
                from core.research.policy import ResearchPolicy
                from core.research.fallback import ResearchFallbackEvaluator
                from core.research.service import get_web_research_service

                retriever = get_ncert_retriever()
                rag_ctx = retriever.retrieve(user_message, top_k=2)
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

            system = _build_chemistry_system_prompt(
                self._topics or None,
                rag_evidence=rag_evidence,
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
            return get_inference_service().stream_chat(msgs, max_tokens=800)
        except Exception as exc:
            logger.error(f"ChemistryTutorRuntime.stream error: {exc}")
            raise
