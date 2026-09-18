"""Gayatri AI — Chemistry Tutor Runtime.

Deterministic execution block for CHEMISTRY_TUTOR mode.
Builds NCERT-grounded system prompts dynamically from the
curriculum manifest and retrieved NCERT RAG context, routing through the local LLM.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger("gayatri.runtimes.chemistry")


def _build_chemistry_system_prompt(topics: list[str] | None = None, rag_evidence: str = "") -> str:
    """Build the Chemistry Tutor system prompt, injecting live curriculum topics and RAG evidence."""
    if topics:
        topics_text = "\n".join(f"  - {t}" for t in topics[:20])  # cap at 20 for prompt length
        curriculum_block = f"Supported NCERT topics in this session:\n{topics_text}"
    else:
        curriculum_block = (
            "Supported domains: Thermodynamics, Inorganic Chemistry (NCERT/CBSE)"
        )

    evidence_block = f"\n\n{rag_evidence}" if rag_evidence else ""

    return f"""You are Gayatri Chemistry Tutor.
You teach Chemistry in an NCERT/CBSE-oriented educational setting.
{curriculum_block}

You are an adaptive teacher. Follow this cycle:
Explain → Example → Ask → Evaluate → Adapt → Continue.

Use supplied source context as the primary authority.
Do not invent citations or source references.
Do not pretend to know information that has not been verified.
Do not act as a coding, mathematics, research, or general-purpose agent.
For unsupported requests, clearly redirect the learner to a relevant chemistry topic.{evidence_block}"""


class ChemistryTutorRuntime:
    """Chemistry Tutor runtime — strict NCERT/CBSE scope with RAG retrieval."""

    def __init__(self):
        self._manifest = None
        self._topics: list[str] = []
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
        """Stream a response for a chemistry tutoring turn with NCERT RAG retrieval."""
        try:
            from legacy.agents.default_agents import _build_messages, _local_chat_stream, _get_tutor_context
            from core.rag.retriever import get_ncert_retriever

            # RAG Retrieval
            rag_evidence = ""
            try:
                retriever = get_ncert_retriever()
                rag_ctx = retriever.retrieve(user_message, top_k=2)
                rag_evidence = rag_ctx.formatted_evidence()
            except Exception as rag_exc:
                logger.warning(f"RAG retrieval skipped: {rag_exc}")

            system = _build_chemistry_system_prompt(self._topics or None, rag_evidence=rag_evidence)
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
