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
from dataclasses import dataclass, field
from typing import Any

from core.agents.registry import agent_registry
from core.agents.runtime import AgentContext, AgentRuntime
from core.config import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, ExecutionMode
from core.conversation import Conversation, ConversationStore
from core.privacy import get_redactor
from core.security.validation import validate_query_text, validate_session_id, validate_student_id

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

        # Question / clarification check (Audit #36): if the student asked a question or asked for help,
        # do not penalize them or treat it as an answer to the previous turn.
        clean_msg = user_message.strip().lower()
        is_question = (
            clean_msg.endswith("?")
            or clean_msg.startswith((
                "what", "why", "how", "can you", "could you", "tell me", "explain",
                "i don't understand", "i dont understand", "idk", "what is", "whats", "who", "which"
            ))
        )
        if is_question:
            logger.info(f"Student asked a question/clarification ('{user_message[:50]}...'). Clearing waiting_for_answer.")
            ctx.waiting_for_answer = False
            tutor.save_context(session_id)
            return

        correct = None
        confidence = 1.0

        # Structured / heuristic evaluation first (Phase 6 / Section 12)
        try:
            from core.tutor.evaluator import StudentAnswerEvaluator
            eval_result = StudentAnswerEvaluator.evaluate(
                student_answer=user_message,
                concept_id=ctx.current_concept_id,
                question=ctx.concept_description,
            )
            if eval_result.correctness == "correct":
                correct = True
                confidence = eval_result.confidence
            elif eval_result.correctness == "incorrect":
                correct = False
                confidence = eval_result.confidence
            else:
                # If uncertain, attempt quick LLM evaluation only if local provider is available
                from core.providers.local import LocalProvider
                if LocalProvider.is_available():
                    system_prompt = (
                        f"You are an educational evaluator. The student is learning '{ctx.current_concept_name}'.\n"
                        f"Concept description: {ctx.concept_description}\n\n"
                        "Evaluate the student's answer. Answer ONLY in JSON format: "
                        '{"correct": true, "confidence": 0.9} (use false if incorrect, and null if it is a clarification question or too ambiguous).'
                    )
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
        except Exception as eval_exc:
            logger.debug(f"Evaluator fallback to uncertain: {eval_exc}")
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
    student_id: str | None = None


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
    next_actions: list[dict] = field(default_factory=list)


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
        state_manager: Any = None,
    ):
        self.conversations = conversations if conversations is not None else _conversations
        self._tutor_engine = tutor_engine
        self._ldg = ldg
        self._state_manager = state_manager
        self._lock = threading.RLock()

    def get_state_manager(self) -> Any:
        with self._lock:
            if self._state_manager is None:
                from core.tutor.state import TutorStateManager
                self._state_manager = TutorStateManager()
            return self._state_manager

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

        try:
            session_id = validate_session_id(session_id)
            student_id = getattr(opts, "student_id", None) or session_id
            validate_student_id(student_id)
            user_message = validate_query_text(user_message)
            mode = self._validate_mode(opts)
            user_message = _redact_pii(user_message)
            conv = self._get_conversation(session_id)
            conv.mode = mode
        
        except ValueError as e:
            from core.errors import sanitize_error
            from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
            sanitized = sanitize_error(e, category="orchestrator_submit")
            latency = (time.time() - start) * 1000
            actions = DeadEndResolver.resolve_actions(DeadEndScenario.ACTIVE_LEARNING, ActionPath.FAILURE)
            return TurnResult(
                text=f"I encountered an error: {sanitized.user_message}",
                model_used="local",
                routing_reason="input_validation_failed",
                latency_ms=latency,
                execution_mode=exec_mode.value,
                status="ERROR",
                next_actions=[a.to_dict() for a in actions],
            )

        from core.security.rate_limiter import get_governor, RateLimitExceededError
        governor = get_governor()

        try:
            governor.check_turn(student_id, session_id)
        except RateLimitExceededError as rle:
            latency = (time.time() - start) * 1000
            from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
            actions = DeadEndResolver.resolve_actions(DeadEndScenario.ACTIVE_LEARNING, ActionPath.RECOVERY)
            return TurnResult(
                text=str(rle),
                model_used="local",
                routing_reason="rate_limit_exceeded",
                latency_ms=latency,
                execution_mode=exec_mode.value,
                status="ERROR",
                next_actions=[a.to_dict() for a in actions],
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
            with governor.concurrency_guard():
                from core.mode import AppMode
                if mode == AppMode.CHEMISTRY_TUTOR.value:
                    from core.tutor.state import TutorStateManager, generate_turn_id
                    from core.tutor.lifecycle import TurnLifecycleManager, TurnStage

                    student_id = getattr(opts, "student_id", None) or session_id
                    turn_id, _ = generate_turn_id(student_id=student_id, session_id=session_id)
                    state_mgr = self.get_state_manager()
                    lifecycle = TurnLifecycleManager(state_mgr)

                    tutor_eng = self.get_tutor_engine()
                    tutor_txn = None
                    if tutor_eng and hasattr(tutor_eng, "begin_transaction"):
                        tutor_txn = tutor_eng.begin_transaction(session_id)

                    # 1. TURN_STARTED
                    lifecycle.start_turn(turn_id, student_id, session_id)

                    try:
                        # 2. EVALUATION_STARTED
                        lifecycle.update_stage(turn_id, TurnStage.EVALUATION_STARTED)
                        _evaluate_tutor_response(session_id, user_message, tutor=tutor_eng, ldg=self.get_ldg())
                        _inject_tutor_context(context, session_id, tutor=tutor_eng, ldg=self.get_ldg())

                        from core.runtimes.chemistry import ChemistryTutorRuntime
                        runtime = ChemistryTutorRuntime()
                        stream = runtime.stream(user_message, context)
                        resp_text = "".join([t for t in stream])

                        # 3. RESPONSE_GENERATED
                        lifecycle.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)

                        # 4. EVALUATION_COMPLETED
                        lifecycle.update_stage(turn_id, TurnStage.EVALUATION_COMPLETED)

                        _post_tutor_response(session_id, tutor=tutor_eng)

                        # 5. LEARNING_STATE_UPDATED
                        lifecycle.update_stage(turn_id, TurnStage.LEARNING_STATE_UPDATED)

                        if tutor_txn:
                            tutor_txn.commit()

                        # 6. TURN_COMMITTED
                        lifecycle.update_stage(turn_id, TurnStage.TURN_COMMITTED)
                    except Exception as e:
                        if tutor_txn:
                            tutor_txn.rollback()
                        lifecycle.update_stage(turn_id, TurnStage.TURN_ABORTED, error_detail=str(e))
                        raise e
                else:
                    from core.runtimes.general import GeneralAssistantRuntime
                    runtime = GeneralAssistantRuntime()
                    stream = runtime.stream(user_message, context)
                    resp_text = "".join([t for t in stream])

                conv.add("user", user_message, agent_name=agent_name)
                conv.add("assistant", resp_text, agent_name=agent_name)
                
                from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
                tutor_ctx = self.get_tutor_engine().get_or_create_context(session_id) if self.get_tutor_engine() else None
                resolved_context = {
                    "concept_name": tutor_ctx.current_concept_name if tutor_ctx else "Thermodynamics",
                    "concept_id": tutor_ctx.current_concept_id if tutor_ctx else "thermo.first_law",
                    "target_mode": mode,
                }
                scenario = DeadEndScenario.ACTIVE_LEARNING if mode == AppMode.CHEMISTRY_TUTOR.value else DeadEndScenario.MODE_SWITCH
                actions = DeadEndResolver.resolve_actions(scenario, ActionPath.SUCCESS, resolved_context)
                
                return TurnResult(
                    text=resp_text,
                    model_used="local",
                    routing_reason="mode_dispatch",
                    latency_ms=(time.time() - start) * 1000,
                    agent_name=agent_name,
                    execution_mode=exec_mode.value,
                    status="SUCCESS",
                    next_actions=[a.to_dict() for a in actions],
                )
        except Exception as exc:
            from core.errors import sanitize_error
            from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
            sanitized = sanitize_error(exc, category="orchestrator_submit")
            conv.add("user", user_message)
            latency = (time.time() - start) * 1000
            sc = DeadEndScenario.LLM_TIMEOUT if isinstance(exc, TimeoutError) else DeadEndScenario.ACTIVE_LEARNING
            actions = DeadEndResolver.resolve_actions(sc, ActionPath.FAILURE)
            return TurnResult(
                text=f"I encountered an error: {sanitized.user_message}",
                model_used="local",
                routing_reason=f"error:{type(exc).__name__}",
                latency_ms=latency,
                execution_mode=exec_mode.value,
                status="ERROR",
                next_actions=[a.to_dict() for a in actions],
            )

    def stream(self, user_message: str, session_id: str = "default",
               options: TurnOptions | None = None):
        opts = options or TurnOptions()
        exec_mode = _get_execution_mode()

        try:
            session_id = validate_session_id(session_id)
            student_id = getattr(opts, "student_id", None) or session_id
            validate_student_id(student_id)
            user_message = validate_query_text(user_message)
            mode = self._validate_mode(opts)
            user_message = _redact_pii(user_message)
            conv = self._get_conversation(session_id)
            conv.mode = mode
        
        except ValueError as e:
            yield str(e), True
            return

        from core.security.rate_limiter import get_governor, RateLimitExceededError
        governor = get_governor()

        try:
            governor.check_turn(student_id, session_id)
        except RateLimitExceededError as rle:
            yield str(rle), True
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
        
        try:
            with governor.concurrency_guard():
                from core.mode import AppMode
                if mode == AppMode.CHEMISTRY_TUTOR.value:
                    from core.tutor.state import TutorStateManager, generate_turn_id
                    from core.tutor.lifecycle import TurnLifecycleManager, TurnStage

                    student_id = getattr(opts, "student_id", None) or session_id
                    turn_id, _ = generate_turn_id(student_id=student_id, session_id=session_id)
                    state_mgr = self.get_state_manager()
                    lifecycle = TurnLifecycleManager(state_mgr)

                    tutor_eng = self.get_tutor_engine()
                    tutor_txn = None
                    if tutor_eng and hasattr(tutor_eng, "begin_transaction"):
                        tutor_txn = tutor_eng.begin_transaction(session_id)

                    # 1. TURN_STARTED
                    try:
                        lifecycle.start_turn(turn_id, student_id, session_id)
                    except Exception as lce:
                        logger.warning(f"Lifecycle start_turn warning: {lce}")

                    try:
                        # 2. EVALUATION_STARTED
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.EVALUATION_STARTED)
                        except Exception as lce:
                            logger.warning(f"Lifecycle EVALUATION_STARTED warning: {lce}")

                        _evaluate_tutor_response(session_id, user_message, tutor=tutor_eng, ldg=self.get_ldg())
                        _inject_tutor_context(context, session_id, tutor=tutor_eng, ldg=self.get_ldg())

                        from core.runtimes.chemistry import ChemistryTutorRuntime
                        runtime = ChemistryTutorRuntime()

                        token_stream = runtime.stream(user_message, context)
                        for token in token_stream:
                            buffer.append(token)
                            yield token, False

                        # 3. RESPONSE_GENERATED
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)
                        except Exception as lce:
                            logger.warning(f"Lifecycle RESPONSE_GENERATED warning: {lce}")

                        # 4. EVALUATION_COMPLETED
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.EVALUATION_COMPLETED)
                        except Exception as lce:
                            logger.warning(f"Lifecycle EVALUATION_COMPLETED warning: {lce}")

                        try:
                            _post_tutor_response(session_id, tutor=tutor_eng)
                        except Exception as pte:
                            logger.warning(f"Post tutor response warning: {pte}")

                        # 5. LEARNING_STATE_UPDATED
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.LEARNING_STATE_UPDATED)
                        except Exception as lce:
                            logger.warning(f"Lifecycle LEARNING_STATE_UPDATED warning: {lce}")

                        if tutor_txn:
                            try:
                                tutor_txn.commit()
                            except Exception as tce:
                                logger.warning(f"Tutor transaction commit warning: {tce}")

                        # 6. TURN_COMMITTED
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.TURN_COMMITTED)
                        except Exception as lce:
                            logger.warning(f"Lifecycle TURN_COMMITTED warning: {lce}")
                    except Exception as e:
                        if tutor_txn:
                            try:
                                tutor_txn.rollback()
                            except Exception:
                                pass
                        try:
                            lifecycle.update_stage(turn_id, TurnStage.TURN_ABORTED, error_detail=str(e))
                        except Exception:
                            pass
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
        except RateLimitExceededError as rle:
            yield str(rle), True
            return

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
