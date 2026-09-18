"""Gayatri AI — Chemistry Tutor Runtime.

Deterministic execution block for CHEMISTRY_TUTOR mode.
Integrates Tutor State Machine, Intent Classifier, Student Adapter, Memory Manager,
Pedagogical Policies (Explanation, Numerical, Reaction), Evaluator, Out-of-Domain Guard,
and NCERT RAG context into local LLM prompt construction.
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

logger = logging.getLogger("gayatri.runtimes.chemistry")


def _build_chemistry_system_prompt(
    topics: list[str] | None = None,
    rag_evidence: str = "",
    policy_directive: str = "",
    memory_summary: str = "",
) -> str:
    """Build the Chemistry Tutor system prompt, injecting live curriculum, RAG evidence, policy, and memory."""
    if topics:
        topics_text = "\n".join(f"  - {t}" for t in topics[:20])  # cap at 20 for prompt length
        curriculum_block = f"Supported NCERT topics in this session:\n{topics_text}"
    else:
        curriculum_block = (
            "Supported domains: Thermodynamics, Inorganic Chemistry (NCERT/CBSE)"
        )

    evidence_block = f"\n\n{rag_evidence}" if rag_evidence else ""
    directive_block = f"\n\n{policy_directive}" if policy_directive else ""
    memory_block = f"\n\n{memory_summary}" if memory_summary else ""

    return f"""You are Gayatri Chemistry Tutor.
You teach Chemistry in an NCERT/CBSE-oriented educational setting.
{curriculum_block}

You are an adaptive teacher. Follow this cycle:
Explain → Example → Ask → Evaluate → Adapt → Continue.

Use supplied source context as the primary authority.
Do not invent citations or source references.
Do not pretend to know information that has not been verified.
Do not act as a coding, mathematics, research, or general-purpose agent.
For unsupported requests, clearly redirect the learner to a relevant chemistry topic.{memory_block}{directive_block}{evidence_block}"""


class ChemistryTutorRuntime:
    """Chemistry Tutor runtime — strict NCERT/CBSE scope with State Machine and RAG retrieval."""

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
        """Stream a response for a chemistry tutoring turn with full state machine and policy routing."""
        try:
            from legacy.agents.default_agents import _build_messages, _local_chat_stream, _get_tutor_context
            from core.rag.retriever import get_ncert_retriever

            # 1. Check Out-of-Domain Guard
            if OutOfDomainGuard.is_out_of_domain(user_message):
                policy_directive = OutOfDomainGuard.get_redirection_prompt(user_message)
                system = _build_chemistry_system_prompt(self._topics or None, policy_directive=policy_directive)
                msgs = _build_messages(system, user_message, getattr(context, "history", None))
                return _local_chat_stream(msgs, max_tokens=300)

            # 2. Intent Classification & State Machine Transition
            intent = TutorIntentClassifier.classify(user_message)
            if intent == TutorIntent.SOLVE:
                self.state_machine.transition_to(TutorState.EXPLAINING)
                policy_directive = NumericalPolicy.get_directive()
            elif intent == TutorIntent.PRACTICE:
                self.state_machine.transition_to(TutorState.PRACTICING)
                policy_directive = NumericalPolicy.get_directive()
            elif intent in (TutorIntent.EXPLAIN, TutorIntent.LEARN):
                self.state_machine.transition_to(TutorState.EXPLAINING)
                policy_directive = ExplanationPolicy.get_directive("Thermodynamics", "General", "medium")
            else:
                policy_directive = ExplanationPolicy.get_directive("Chemistry", "General", "medium")

            # 3. Student Answer Evaluation if checking or evaluating
            eval_result = StudentAnswerEvaluator.evaluate(user_message)
            adaptation = StudentAdapter.adapt(mastery_score=eval_result.confidence)

            # 4. Memory summary block
            memory = TutorMemoryManager.build_memory(
                topic="Thermodynamics",
                mastery=eval_result.confidence,
                difficulty=adaptation.target_difficulty,
            )

            # 5. RAG Retrieval
            rag_evidence = ""
            try:
                retriever = get_ncert_retriever()
                rag_ctx = retriever.retrieve(user_message, top_k=2)
                rag_evidence = rag_ctx.formatted_evidence()
            except Exception as rag_exc:
                logger.warning(f"RAG retrieval skipped: {rag_exc}")

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
            return _local_chat_stream(msgs, max_tokens=400)
        except Exception as exc:
            logger.error(f"ChemistryTutorRuntime.stream error: {exc}")
            raise
