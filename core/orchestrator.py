"""Gayatri AI — Orchestrator: routes a user turn through agents → model → response.

LDG integration: when the Tutor agent is invoked, the orchestrator:
1. Loads the Learning Dependency Graph
2. Selects the next appropriate concept
3. Injects concept context into AgentContext.metadata
4. After the turn, updates mastery based on student response
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from core.agents.registry import agent_registry
from core.agents.runtime import AgentContext, AgentRuntime
from core.config import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, ExecutionMode
from core.conversation import Conversation, ConversationStore
from core.privacy import get_redactor

logger = logging.getLogger("gayatri.orchestrator")

# Global conversation store — one conversation per session
_conversations = ConversationStore()

# LDG and TutorEngine lazy init with reentrant lock
_init_lock = threading.RLock()
_ldg: Any = None
_tutor_engine: Any = None


def _get_ldg():
    """Lazy-load the Learning Dependency Graph with default curriculum."""
    global _ldg
    if _ldg is None:
        with _init_lock:
            if _ldg is None:
                try:
                    from core.config import LDG_CURICULUM_DIR
                    from core.knowledge_graph import LearningDependencyGraph, load_curriculum
                    ldg = LearningDependencyGraph()
                    curriculum_path = LDG_CURICULUM_DIR / "python_basics.json"
                    if curriculum_path.exists():
                        load_curriculum(ldg, curriculum_path)
                        logger.info(f"LDG loaded: {curriculum_path}")
                    else:
                        logger.info("LDG initialized (no default curriculum)")
                    _ldg = ldg
                except Exception as exc:
                    logger.error(f"LDG init failed: {exc}")
                    _ldg = None
    return _ldg


def _get_tutor_engine():
    """Lazy-load the Tutor Engine with LDG."""
    global _tutor_engine
    if _tutor_engine is None:
        with _init_lock:
            if _tutor_engine is None:
                try:
                    from core.tutor_engine import TutorEngine
                    ldg = _get_ldg()
                    if ldg:
                        _tutor_engine = TutorEngine(ldg)
                        logger.info("TutorEngine initialized")
                    else:
                        logger.warning("TutorEngine: LDG not available")
                except Exception as exc:
                    logger.error(f"TutorEngine init failed: {exc}")
                    _tutor_engine = None
    return _tutor_engine


def _redact_pii(text: str) -> str:
    """Redact PII before sending to model."""
    redactor = get_redactor()
    result = redactor.redact(text)
    if result.has_pii:
        logger.info(f"PII redacted: {redactor.get_redaction_summary(result)}")
    return result.clean_text


def _get_execution_mode() -> ExecutionMode:
    """Read the current privacy/execution mode from settings."""
    try:
        from core.settings import get_settings
        settings = get_settings()
        if settings.get("router_preference") == "local_only":
            return ExecutionMode.LOCAL_ONLY
        mode_str = settings.get("privacy_mode", "local_only")
        return ExecutionMode(mode_str)
    except (ValueError, Exception):
        # Default to safest mode
        return ExecutionMode.LOCAL_ONLY


def _inject_tutor_context(context: AgentContext, session_id: str,
                          tutor: Any = None, ldg: Any = None) -> None:
    """Inject LDG concept context into AgentContext.metadata for Tutor agent.

    Side-effect: mutates context.metadata in place.
    """
    tutor = tutor or _get_tutor_engine()
    ldg = ldg or _get_ldg()
    if not tutor or not ldg:
        return

    try:
        engine = tutor
        ctx = engine.get_or_create_context(session_id)
        concept = engine.get_next_concept_for_session(session_id)

        if concept:
            # Check if prerequisites are met
            prereqs = ldg.get_prerequisites(concept.id)
            prereq_names = []
            prerequisites_not_met = False
            for pid in prereqs:
                pc = ldg.get_concept(pid)
                if pc and (ldg.get_mastery(pid) or 0.0) < 0.85:
                    prerequisites_not_met = True
                    prereq_names.append(pc.name)

            tutor_meta = {
                "concept_id": concept.id,
                "concept_name": concept.name,
                "concept_description": concept.description,
                "mastery_pct": f"{int(concept.mastery * 100)}%",
                "waiting_for_answer": ctx.waiting_for_answer,
                "prerequisites_not_met": prerequisites_not_met,
                "prereq_names": prereq_names,
            }

            # If waiting for answer, mark that
            if ctx.waiting_for_answer:
                tutor_meta["waiting_for_answer"] = True

            if getattr(ctx, 'last_attempt_correct', None) is not None:
                tutor_meta["recent_attempt"] = {"correct": ctx.last_attempt_correct}
                ctx.last_attempt_correct = None

            if not hasattr(context, 'metadata') or context.metadata is None:
                context.metadata = {}
            context.metadata["tutor"] = tutor_meta
            logger.debug(f"Injected tutor context: {concept.name} (mastery={concept.mastery:.2f})")
    except Exception as exc:
        logger.error(f"Failed to inject tutor context: {exc}")


def _evaluate_tutor_response(session_id: str, user_message: str,
                             tutor: Any = None, ldg: Any = None) -> None:
    """Evaluate student response and update LDG mastery.

    Called during the Tutor agent turn before generating response.
    Uses heuristic detection with staleness, duplicate, and question checks (Audit #36 & #130).
    """
    tutor = tutor or _get_tutor_engine()
    ldg = ldg or _get_ldg()
    if not tutor or not ldg:
        return

    try:
        ctx = tutor.get_or_create_context(session_id)
        if not ctx.current_concept_id:
            return

        # Staleness check (Audit #130): only evaluate if tutor was actively waiting
        if not tutor.is_waiting_for_answer(session_id):
            return

        system_prompt = (
            f"You are an educational evaluator. The student is learning '{ctx.current_concept_name}'.\n"
            f"Concept description: {ctx.concept_description}\n\n"
            "Evaluate the student's answer. Answer ONLY in JSON format: "
            '{"correct": true, "confidence": 0.9} (use false if incorrect, and null if it is a clarification question or too ambiguous).'
        )

        correct = None
        confidence = 1.0

        try:
            from core.providers.local import LocalProvider
            import json
            eval_resp = LocalProvider.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ], max_tokens=20, temperature=0.1)
            
            clean_resp = eval_resp.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp[7:]
            if clean_resp.startswith("```"):
                clean_resp = clean_resp[3:]
            if clean_resp.endswith("```"):
                clean_resp = clean_resp[:-3]
            clean_resp = clean_resp.strip()

            result = json.loads(clean_resp)
            correct = result.get("correct")
            conf = result.get("confidence")
            if isinstance(conf, (int, float)):
                confidence = float(conf)
                
            logger.info(f"LLM evaluation for '{ctx.current_concept_name}': correct={correct}, confidence={confidence:.2f}")
        except Exception as llm_exc:
            logger.warning(f"LLM evaluator failed or returned invalid JSON: {llm_exc}. Defaulting to uncertain.")
            correct = None

        mastery = tutor.record_student_response(
            session_id,
            correct=correct,
            confidence=confidence,
            student_answer=user_message,
        )
        logger.info(
            f"Evaluated response for {ctx.current_concept_name}: "
            f"{'correct' if correct else 'incorrect' if correct is False else 'uncertain'}, mastery={mastery:.3f}"
        )
    except Exception as exc:
        logger.error(f"Failed to evaluate tutor response: {exc}")


def _post_tutor_response(session_id: str, tutor: Any = None) -> None:
    """Mark the tutor as waiting for an answer after it responds."""
    tutor = tutor or _get_tutor_engine()
    if tutor:
        tutor.set_waiting_for_answer(session_id)


_TASK_TYPE_AGENTS: dict[str, str] = {
    "tutor": "Tutor",
    "practice": "Practice Generator",
    "quiz": "Practice Generator",
    "code": "Code Reviewer",
    "review": "Code Reviewer",
    "orchestrate": "Orchestrator Agent",
    "plan": "Orchestrator Agent",
}


@dataclass
class TurnOptions:
    """Options for a single turn."""
    mode: str = "general_assistant"
    task_type: str = "auto"
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    model_override: str | None = None
    forced_tier: str | None = None
    forced_agent: str | None = None


@dataclass
class TurnResult:
    """Result of processing one turn."""
    text: str
    model_used: str = "local"
    routing_reason: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    agent_name: str = ""
    execution_mode: str = "local_only"  # "local_only" | "cloud_allowed"
    status: str = "SUCCESS"  # "SUCCESS" | "MODEL_UNAVAILABLE" | "ERROR"


class Orchestrator:
    """Routes user messages through the active mode runtime.
    """

    def __init__(
        self,
        registry=None,
        runtime=None,
        conversations: ConversationStore | None = None,
        tutor_engine: Any = None,
        ldg: Any = None,
    ):
        self.conversations = conversations if conversations is not None else _conversations
        self._tutor_engine = tutor_engine
        self._ldg = ldg
        self._lock = threading.RLock()

    def get_tutor_engine(self) -> Any:
        if self._tutor_engine is not None:
            return self._tutor_engine
        return _get_tutor_engine()

    def get_ldg(self) -> Any:
        if self._ldg is not None:
            return self._ldg
        return _get_ldg()

    def _get_conversation(self, session_id: str) -> Conversation:
        return self.conversations.get(session_id)

    def _validate_mode(self, opts: TurnOptions) -> str:
        from core.mode import AppMode
        # Check if they are trying to force a legacy agent
        if opts.forced_agent and opts.forced_agent.lower() not in ["", "auto", "chemistry_tutor", "general_assistant"]:
            raise ValueError(f"Legacy agent '{opts.forced_agent}' is rejected. Please select a valid mode.")
        if opts.task_type and opts.task_type.lower() not in ["", "auto", "chemistry_tutor", "general_assistant"]:
             # In tests, they might pass "tutor", "math" as task_type. Reject legacy ones.
             task = opts.task_type.lower()
             if task in ["math", "code", "code_review", "research_agent"]:
                 raise ValueError(f"Legacy task type '{opts.task_type}' is rejected.")
        
        mode_val = opts.mode
        try:
            return AppMode(mode_val).value
        except ValueError:
            raise ValueError(f"Unknown mode: {mode_val}")

    def submit(self, user_message: str, session_id: str = "default",
               options: TurnOptions | None = None) -> TurnResult:
        opts = options or TurnOptions()
        start = time.time()
        exec_mode = _get_execution_mode()
        
        user_message = _redact_pii(user_message)
        conv = self._get_conversation(session_id)

        try:
            mode = self._validate_mode(opts)
            conv.mode = mode
        
        except ValueError as e:
            from core.errors import sanitize_error
            sanitized = sanitize_error(e, category="orchestrator_submit")
            latency = (time.time() - start) * 1000
            return TurnResult(
                text=f"I encountered an error: {sanitized.user_message}",
                model_used="local",
                routing_reason="mode_validation_failed",
                latency_ms=latency,
                execution_mode=exec_mode.value,
                status="ERROR"
            )

        context = AgentContext(
            session_id=session_id,
            user_message=user_message,
            model_tier=opts.forced_tier or "local",
            model_override=opts.model_override,
            history=conv.get_messages_for_model()[-50:],
        )

        resp_text = ""
        agent_name = mode
        
        try:
            from core.mode import AppMode
            if mode == AppMode.CHEMISTRY_TUTOR.value:
                tutor_eng = self.get_tutor_engine()
                tutor_txn = None
                if tutor_eng and hasattr(tutor_eng, "begin_transaction"):
                    tutor_txn = tutor_eng.begin_transaction(session_id)

                _evaluate_tutor_response(session_id, user_message, tutor=tutor_eng, ldg=self.get_ldg())
                _inject_tutor_context(context, session_id, tutor=tutor_eng, ldg=self.get_ldg())
                
                from core.runtimes.chemistry import ChemistryTutorRuntime
                runtime = ChemistryTutorRuntime()
                try:
                    stream = runtime.stream(user_message, context)
                    resp_text = "".join([t for t in stream])
                    _post_tutor_response(session_id, tutor=tutor_eng)
                    if tutor_txn:
                        tutor_txn.commit()
                except Exception as e:
                    if tutor_txn:
                        tutor_txn.rollback()
                    raise e
            else:
                from core.runtimes.general import GeneralAssistantRuntime
                runtime = GeneralAssistantRuntime()
                stream = runtime.stream(user_message, context)
                resp_text = "".join([t for t in stream])

            conv.add("user", user_message, agent_name=agent_name)
            conv.add("assistant", resp_text, agent_name=agent_name)
            
            return TurnResult(
                text=resp_text,
                model_used="local",
                routing_reason="mode_dispatch",
                latency_ms=(time.time() - start) * 1000,
                agent_name=agent_name,
                execution_mode=exec_mode.value,
                status="SUCCESS"
            )
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="orchestrator_submit")
            conv.add("user", user_message)
            latency = (time.time() - start) * 1000
            return TurnResult(
                text=f"I encountered an error: {sanitized.user_message}",
                model_used="local",
                routing_reason=f"error:{type(exc).__name__}",
                latency_ms=latency,
                execution_mode=exec_mode.value,
                status="ERROR",
            )

    def stream(self, user_message: str, session_id: str = "default",
               options: TurnOptions | None = None):
        opts = options or TurnOptions()
        exec_mode = _get_execution_mode()
        
        user_message = _redact_pii(user_message)
        conv = self._get_conversation(session_id)

        try:
            mode = self._validate_mode(opts)
            conv.mode = mode
        
        except ValueError as e:
            yield str(e), True
            return

        context = AgentContext(
            session_id=session_id,
            user_message=user_message,
            model_tier=opts.forced_tier or "local",
            model_override=opts.model_override,
            history=conv.get_messages_for_model()[-50:],
        )

        agent_name = mode
        buffer = []
        
        from core.mode import AppMode
        if mode == AppMode.CHEMISTRY_TUTOR.value:
            tutor_eng = self.get_tutor_engine()
            tutor_txn = None
            if tutor_eng and hasattr(tutor_eng, "begin_transaction"):
                tutor_txn = tutor_eng.begin_transaction(session_id)

            _inject_tutor_context(context, session_id, tutor=tutor_eng, ldg=self.get_ldg())
            
            import threading
            def _run_eval():
                _evaluate_tutor_response(session_id, user_message, tutor=tutor_eng, ldg=self.get_ldg())
            threading.Thread(target=_run_eval, daemon=True, name="Gayatri-Evaluator").start()

            from core.runtimes.chemistry import ChemistryTutorRuntime
            runtime = ChemistryTutorRuntime()
            try:
                token_stream = runtime.stream(user_message, context)
                for token in token_stream:
                    buffer.append(token)
                    yield token, False
                _post_tutor_response(session_id, tutor=tutor_eng)
                if tutor_txn:
                    tutor_txn.commit()
            except Exception as e:
                if tutor_txn:
                    tutor_txn.rollback()
                yield str(e), True
                return
        else:
            from core.runtimes.general import GeneralAssistantRuntime
            runtime = GeneralAssistantRuntime()
            try:
                token_stream = runtime.stream(user_message, context)
                for token in token_stream:
                    buffer.append(token)
                    yield token, False
            except Exception as e:
                yield str(e), True
                return

        resp_text = "".join(buffer)
        conv.add("user", user_message, agent_name=agent_name)
        conv.add("assistant", resp_text, agent_name=agent_name)
        yield "", True

    def clear_session(self, session_id: str = "default") -> None:
        with self._lock:
            conv = self._get_conversation(session_id)
            conv.clear()
            tutor = self.get_tutor_engine()
            if tutor and hasattr(tutor, "clear_session"):
                tutor.clear_session(session_id)
            try:
                from core.session import get_session_store
                get_session_store().clear_session_messages(session_id)
            except Exception as exc:
                logger.debug(f"Could not clear persisted session {session_id}: {exc}")

    def get_conversation(self, session_id: str = "default") -> Conversation:
        return self._get_conversation(session_id)

    def new_session(self, session_id: str = "default") -> Conversation:
        return self.conversations.new_session(session_id)

    def load_session(self, session_id: str, messages: list[dict], tutor_context: Any = None) -> Conversation:
        with self._lock:
            conv = self.new_session(session_id)
            for msg in messages:
                conv.add(msg["role"], msg["content"], agent_name=msg.get("agent_name", ""))
            tutor = self.get_tutor_engine()
            if tutor:
                if tutor_context is not None:
                    if hasattr(tutor, "set_context"):
                        tutor.set_context(session_id, tutor_context)
                    else:
                        tutor.session_contexts[session_id] = tutor_context
                else:
                    tutor.get_or_create_context(session_id)
            return conv
