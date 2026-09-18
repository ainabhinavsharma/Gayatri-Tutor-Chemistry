"""Gayatri AI — QWebChannel Bridge (JS ⇄ Python).

Updated to use real settings persistence, provider management, and model catalog.
"""

from __future__ import annotations

import json
import threading

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from core.logging_setup import setup_logging
from core.model_fetch.ollama_pull import OllamaPullError

logger = setup_logging()


class Bridge(QObject):
    """Exposes async slots and streaming signals to the UI via QWebChannel.

    Signals (visible from JS):
        token(int idx, str text) — streaming token
        done() — response complete
        error(str message) — error occurred
    """

    token = Signal(int, str)
    done = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        import uuid
        super().__init__(parent)
        self._view: QWebEngineView | None = None
        self._window: QMainWindow | None = None
        self._orchestrator = None
        self._generation_active = False
        self._session_id = str(uuid.uuid4())

    def _get_orchestrator(self):
        from core.agents.runtime import AgentRuntime

        from core.agents.registry import agent_registry

        from core.orchestrator import Orchestrator

        """Lazy-load the orchestrator."""
        if self._orchestrator is None:
            

            self._orchestrator = Orchestrator(
                registry=agent_registry,
                runtime=AgentRuntime(registry=agent_registry),
            )
        return self._orchestrator

    def _save_session_by_id(self, session_id: str):
        try:
            if not self._orchestrator or not session_id:
                return
            from core.session import get_session_store, validate_session_id
            session_id = validate_session_id(session_id)
            conv = self._orchestrator.get_conversation(session_id)
            if conv and conv.get_all():
                from core.tutor_engine import get_tutor_engine
                store = get_session_store()
                tutor = self._orchestrator.get_tutor_engine() if hasattr(self._orchestrator, "get_tutor_engine") else get_tutor_engine()
                tutor_ctx = tutor.session_contexts.get(session_id) if tutor else None
                store.save_session(session_id, conv, tutor_context=tutor_ctx)
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_save_session")
            self.error.emit(f"Warning: Failed to save session: {sanitized.user_message}")

    def _save_current_session(self):
        self._save_session_by_id(self._session_id)

    def set_view(self, view: QWebEngineView):
        self._view = view

    def set_window(self, window: QMainWindow):
        self._window = window

    # ── Window Controls (Frameless UI) ──────────────────────────────────

    @Slot()
    def minimize_window(self):
        """Minimize the desktop window."""
        if self._window:
            self._window.showMinimized()

    @Slot()
    def maximize_window(self):
        """Toggle maximize / restore the desktop window."""
        if self._window:
            if self._window.isMaximized():
                self._window.showNormal()
            else:
                self._window.showMaximized()

    @Slot()
    def close_window(self):
        """Close the desktop window."""
        if self._window:
            self._window.close()
        else:
            QApplication.quit()

    # ── Slots (callable from JavaScript) ────────────────────────────────

    @Slot(str)
    @Slot(str, str)
    def send_message(self, message: str, mode: str = "general_assistant"):
        """Receive a user message, route through agent/model, stream tokens back (Audit #52 & #53)."""
        if self._generation_active:
            self.error.emit("Please wait for the current response to finish.")
            return

        orch = self._get_orchestrator()
        self._generation_active = True
        generation_session_id = self._session_id

        opts = None
        if mode and mode.lower() != "auto":
            from core.orchestrator import TurnOptions
            opts = TurnOptions(mode=mode)

        def _worker():
            try:
                import time
                buffer = []
                last_emit = time.time()
                for token, is_done in orch.stream(message, session_id=generation_session_id, options=opts):
                    # Verify session hasn't switched during generation (Audit #134)
                    if self._session_id != generation_session_id:
                        logger.warning(
                            f"Active session changed from {generation_session_id} to {self._session_id} "
                            "during streaming; discarding output for superseded session."
                        )
                        break

                    if token:
                        buffer.append(token)

                    now = time.time()
                    if buffer and (now - last_emit >= 0.05 or is_done):
                        self.token.emit(0, "".join(buffer))
                        buffer.clear()
                        last_emit = now

                    if is_done:
                        self._save_session_by_id(generation_session_id)
                        self.done.emit()
                        return

                # If generator exhausted without yielding is_done=True
                if self._session_id == generation_session_id:
                    self._save_session_by_id(generation_session_id)
                    self.done.emit()
            except Exception as exc:
                from core.errors import sanitize_error
                sanitized = sanitize_error(exc, category="bridge_send_message")
                if self._session_id == generation_session_id:
                    self.error.emit(sanitized.user_message)
                    self.done.emit()
            finally:
                self._generation_active = False

        import threading
        t = threading.Thread(target=_worker, daemon=True, name="Gayatri-Inference-Worker")
        t.start()
        # In test runners (pytest / pytest-qt), wait for worker completion and flush event loop
        import os
        if "PYTEST_CURRENT_TEST" in os.environ:
            t.join()
            from PySide6.QtCore import QCoreApplication
            app = QCoreApplication.instance()
            if app:
                app.processEvents()

    @Slot()
    def cancel_generation(self):
        """Cancel the current LLM generation."""
        if self._generation_active:
            from core.providers.local import LocalProvider
            LocalProvider.cancel()
            logger.info("Cancellation signal sent to generation worker.")
        else:
            logger.debug("Cancellation requested but no generation is active.")

    @Slot()
    def new_chat(self):
        """Start a new conversation."""
        if self._generation_active:
            self.error.emit("Cannot start a new chat while a response is generating.")
            return
        import uuid
        self._save_current_session()
        self._session_id = str(uuid.uuid4())
        orch = self._get_orchestrator()
        orch.new_session(self._session_id)
        logger.info(f"New chat started: {self._session_id}")

    @Slot(result=str)
    def get_sessions(self) -> str:
        """Return list of past sessions as JSON."""
        try:
            from core.session import get_session_store
            store = get_session_store()
            sessions = store.list_sessions()
            result = [
                {
                    "id": s["id"],
                    "title": s.get("title", s["id"][:20]),
                    "created_at": s.get("created_at", ""),
                    "updated_at": s.get("updated_at", ""),
                    "message_count": s.get("message_count", 0),
                    "preview": s.get("preview", ""),
                }
                for s in sessions
            ]
            return json.dumps({"ok": True, "sessions": result})
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_get_sessions")
            return json.dumps({
                "ok": False,
                "sessions": [],
                "error": sanitized.user_message,
                "recoverable": True
            })

    @Slot(result=str)
    def get_agents(self) -> str:
        """Return list of available agents with metadata as JSON (Audit #52 & #54)."""
        try:
            self._get_orchestrator()  # ensures default agents are registered
            from core.agents.registry import agent_registry
            agents = agent_registry.list_agents()
            result = [
                {
                    "name": a["name"],
                    "description": a.get("description", ""),
                    "commands": a.get("commands", []),
                    "triggers": a.get("triggers", []),
                }
                for a in agents
            ]
            return json.dumps({"ok": True, "agents": result})
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_get_agents")
            return json.dumps({"ok": False, "agents": [], "error": sanitized.user_message})

    @Slot(result=str)
    def get_curriculum_progress(self) -> str:
        """Return curriculum progress and LDG concepts as JSON (Audit #55)."""
        try:
            orch = self._get_orchestrator()
            ldg = orch.get_ldg() if hasattr(orch, "get_ldg") else None
            if ldg is None:
                from core.knowledge_graph import get_ldg
                ldg = get_ldg()

            if ldg is None:
                return json.dumps({
                    "ok": True,
                    "stats": {"total": 0, "mastered": 0, "in_progress": 0, "mastery_pct": 0.0},
                    "concepts": [],
                })

            stats = ldg.get_progress_stats()
            concepts = []
            for c in ldg.list_concepts():
                concepts.append({
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "subject": c.subject,
                    "difficulty": c.difficulty,
                    "mastery": c.mastery,
                    "mastery_pct": int(c.mastery * 100),
                    "unlocked": ldg.is_unlocked(c.id),
                    "prerequisites": ldg.get_prerequisites(c.id),
                })

            return json.dumps({
                "ok": True,
                "stats": stats,
                "concepts": concepts,
            })
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_get_curriculum_progress")
            return json.dumps({"ok": False, "error": sanitized.user_message, "stats": {}, "concepts": []})

    @Slot(str, str)
    def set_setting(self, key: str, value: str):
        """Persist a setting (value is JSON-stringified from JS)."""
        try:
            from core.settings import _SETTINGS_SCHEMA, get_settings
            store = get_settings()
            # Try to parse as JSON for non-string types
            try:
                parsed = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                parsed = value

            if key not in _SETTINGS_SCHEMA:
                raise ValueError(f"Unknown setting key: '{key}'")

            # Defensively coerce representation if schema expects primitive type
            expected_type = _SETTINGS_SCHEMA[key]
            if expected_type is bool:
                if isinstance(parsed, bool):
                    pass
                elif isinstance(parsed, str):
                    if parsed.lower() in ("true", "1", "yes"):
                        parsed = True
                    elif parsed.lower() in ("false", "0", "no"):
                        parsed = False
                elif isinstance(parsed, (int, float)):
                    parsed = bool(parsed)
            elif expected_type is int:
                if not isinstance(parsed, bool):
                    try:
                        parsed = int(parsed)
                    except (ValueError, TypeError):
                        pass
            elif expected_type is float:
                if not isinstance(parsed, bool):
                    try:
                        parsed = float(parsed)
                    except (ValueError, TypeError):
                        pass

            store.set(key, parsed)
            logger.debug(f"Setting: {key} = {parsed!r}")
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_set_setting")
            self.error.emit(f"Failed to update setting '{key}': {sanitized.user_message}")

    @Slot(str, result=str)
    def get_setting(self, key: str) -> str:
        """Retrieve a setting as JSON string."""
        try:
            from core.settings import get_settings
            store = get_settings()
            value = store.get(key)
            return json.dumps(value)
        except Exception as exc:
            logger.error(f"get_setting('{key}') failed: {exc}", exc_info=True)
            # Return sensible defaults for known settings so UI doesn't break
            defaults = {"privacy_mode": "local_only", "theme": "dark"}
            return json.dumps(defaults.get(key))

    @Slot(result=str)
    def get_local_model_status(self) -> str:
        """Return local model status as JSON."""
        try:
            from core.providers.local import LocalProvider
            health = LocalProvider.health()

            status = {
                "installed": health["available"],
                "name": "gemma-2-2b-it",
                "provider": "local",
                "reason_code": health["reason_code"],
                "message": health["message"],
                "path": health["path"]
            }
            if health["available"] or health["reason_code"] not in ("missing_file", "invalid_file"):
                status["size_mb"] = LocalProvider.MODEL_PATH.stat().st_size / (1024 * 1024) if LocalProvider.MODEL_PATH.exists() else 0

            return json.dumps(status)
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_get_local_model_status")
            return json.dumps({"installed": False, "error": sanitized.user_message, "reason_code": "unknown_error"})

    @Slot(result=str)
    def get_providers(self) -> str:
        """Return list of configured providers with status as JSON."""
        try:
            from core.providers.registry import get_registry
            from core.security.secrets import get_vault

            vault = get_vault()
            registry = get_registry()

            providers = []
            for p in registry.list_providers():
                providers.append({
                    "key": p["key"],
                    "name": p["name"],
                    "has_key": True if p["key"] == "local" else vault.has_key(p["key"]),
                    "available": p["available"],
                })
            return json.dumps(providers)
        except Exception as exc:
            logger.error(f"get_providers error: {exc}")
            return json.dumps([])

    @Slot(str, str, result=str)
    def validate_provider_key(self, provider_key: str, api_key: str) -> str:
        """Validate a provider API key. Returns JSON with result."""
        try:
            from core.providers.registry import get_registry
            registry = get_registry()
            provider = registry.get(provider_key)

            if provider is None:
                return json.dumps({"valid": False, "message": f"Provider '{provider_key}' not found"})

            # P1 DESKTOP-003: Do not mutate the live provider. Create a temporary instance.
            try:
                temp_provider = provider.__class__(api_key=api_key)
            except TypeError:
                try:
                    temp_provider = provider.__class__(api_key)
                except TypeError:
                    temp_provider = provider.__class__()

            if hasattr(temp_provider, 'validate_key'):
                valid, msg = temp_provider.validate_key()
            else:
                valid, msg = False, "Provider doesn't support key validation"

            return json.dumps({"valid": valid, "message": msg})
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_validate_provider_key")
            return json.dumps({"valid": False, "message": sanitized.user_message})

    @Slot(str, str)
    def save_provider_key(self, provider_key: str, api_key: str):
        """Save a provider API key to the vault and update registered provider instance."""
        try:
            from core.providers.registry import get_registry
            from core.security.secrets import get_vault
            vault = get_vault()
            clean_key = api_key.strip()
            if not clean_key:
                vault.delete_key(provider_key)
                logger.info(f"Provider key deleted: {provider_key}")
            else:
                vault.store_key(provider_key, clean_key)
                logger.info(f"Provider key saved: {provider_key}")

            registry = get_registry()
            provider = registry.get(provider_key)
            if provider is not None and hasattr(provider, "_api_key"):
                provider._api_key = clean_key if clean_key else None
                provider._models = None
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_save_provider_key")
            self.error.emit(f"Failed to save key: {sanitized.user_message}")

    @Slot(result=str)
    def get_model_catalog(self) -> str:
        """Return unified model catalog as JSON."""
        try:
            from core.providers.registry import get_registry
            registry = get_registry()
            catalog = registry.to_catalog_dict()
            return json.dumps(catalog)
        except Exception as exc:
            logger.error(f"get_model_catalog error: {exc}")
            return json.dumps([])

    # ── Model Download ─────────────────────────────────────────────────────

    @Slot()
    def download_model(self):
        """Download the model file from Ollama registry in a background thread.

        Emits token signals with progress, done on success, error on failure.
        """
        if getattr(self, '_download_active', False):
            self.error.emit(json.dumps({"status": "error", "message": "Download already in progress"}))
            return

        self._download_cancel = False
        self._download_active = True

        def _run():
            try:
                from core.model_fetch.ollama_pull import pull_model

                def progress(label, downloaded, total):
                    if self._download_cancel:
                        raise OllamaPullError("Cancelled by user")
                    if total > 0:
                        pct = downloaded / total * 100
                        mb = downloaded / 1024 / 1024
                        total_mb = total / 1024 / 1024
                        self.token.emit(0, f"Downloading {label}: {mb:.0f}/{total_mb:.0f} MB ({pct:.0f}%)")
                    else:
                        mb = downloaded / 1024 / 1024
                        self.token.emit(0, f"Downloading {label}: {mb:.0f} MB...")

                result = pull_model(progress_callback=progress)
                size_mb = result["size_mb"]
                self.token.emit(0, f"Download complete: {size_mb:.1f} MB")
                self.token.emit(0, f"Saved to: {result['path']}")
                self.token.emit(0, f"Digest: {result['digest'][:16]}...")
                self.done.emit()

            except Exception as exc:
                from core.errors import sanitize_error
                sanitized = sanitize_error(exc, category="bridge_model_download")
                self.error.emit(json.dumps({"status": "error", "message": sanitized.user_message}))
                self.done.emit()
            finally:
                self._download_active = False
                self._download_cancel = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    @Slot()
    def cancel_model_download(self):
        """Cancel an in-progress model download."""
        self._download_cancel = True
        logger.info("Model download cancel requested")

    @Slot(result=str)
    def install_model(self) -> str:
        """One-shot install: check availability, then download if needed.

        Returns JSON with status. If download is needed, starts async download
        and returns immediately with status "downloading".
        """
        try:
            from core.providers.local import LocalProvider
            health = LocalProvider.health()
            if health["available"]:
                size_mb = LocalProvider.MODEL_PATH.stat().st_size / 1024 / 1024
                return json.dumps({
                    "status": "installed",
                    "path": str(LocalProvider.MODEL_PATH),
                    "size_mb": round(size_mb, 1),
                })

            # Not installed or incomplete — return health reason
            return json.dumps({
                "status": "not_installed",
                "message": health["message"],
                "reason_code": health["reason_code"],
                "expected_path": str(LocalProvider.MODEL_PATH),
            })

        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_install_model")
            return json.dumps({"status": "error", "message": sanitized.user_message})

    @Slot(str)
    def load_session_id(self, session_id: str):
        """Load a previous session into the active conversation."""
        if self._generation_active:
            self.error.emit("Cannot switch session while a response is generating.")
            return
        try:
            from core.session import get_session_store, validate_session_id
            session_id = validate_session_id(session_id)
            self._save_current_session()

            store = get_session_store()
            messages = store.load_session(session_id)
            tutor_ctx = store.load_tutor_context(session_id)

            orch = self._get_orchestrator()
            orch.load_session(session_id, messages, tutor_context=tutor_ctx)
            self._session_id = session_id

            logger.info(f"Loaded session {session_id}: {len(messages)} messages")
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_load_session")
            self.error.emit(f"Failed to load session: {sanitized.user_message}")

    @Slot(str, result=str)
    def delete_session(self, session_id: str) -> str:
        """Delete a saved session from SQLite and in-memory orchestrator."""
        if self._generation_active and self._session_id == session_id:
            return json.dumps({"ok": False, "error": "Cannot delete active generating session."})
        try:
            from core.session import get_session_store, validate_session_id
            session_id = validate_session_id(session_id)
            store = get_session_store()
            store.delete_session(session_id)

            if self._orchestrator:
                self._orchestrator.conversations.delete(session_id)
                tutor = self._orchestrator.get_tutor_engine()
                if tutor and hasattr(tutor, "clear_session"):
                    tutor.clear_session(session_id)

            # If deleting the currently active session, initialize a fresh one
            if self._session_id == session_id:
                import uuid
                self._session_id = str(uuid.uuid4())
                if self._orchestrator:
                    self._orchestrator.new_session(self._session_id)

            return json.dumps({"ok": True, "session_id": session_id})
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="bridge_delete_session")
            return json.dumps({"ok": False, "error": sanitized.user_message})
