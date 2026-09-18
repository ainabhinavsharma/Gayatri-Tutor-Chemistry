import sys
import re

with open('core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add mode to TurnOptions
content = re.sub(
    r'class TurnOptions:\s+"""Options for a single turn."""',
    'class TurnOptions:\n    """Options for a single turn."""\n    mode: str = "general_assistant"',
    content
)

# Replace the Orchestrator methods submit and stream.
# We will just redefine them in the string.
# Finding the class Orchestrator and replacing it.
class_start = content.find('class Orchestrator:')
if class_start == -1:
    print("Could not find class Orchestrator")
    sys.exit(1)

pre_class = content[:class_start]

new_class = '''class Orchestrator:
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
'''

with open('core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(pre_class + new_class)
