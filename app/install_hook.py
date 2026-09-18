"""Gayatri AI — First-run install hook.

Runs at app startup to detect and handle first-run model setup.
Checks if the local model exists; if not, triggers the Ollama registry download.

Usage (from main entry point):
    from app.install_hook import install_hook
    if install_hook.run():
        # Model is ready, proceed with app
        pass
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from core.config import LOCAL_MODEL_FILE, MODELS_DIR

logger = logging.getLogger("gayatri.install_hook")


class InstallHook:
    """Handles first-run model detection and download.

    Call run() at app startup. It checks for the model, downloads if needed,
    and reports progress via callbacks.
    """

    # Primary local model path (fine-tuned Gayatri GGUF)
    EXPECTED_MODEL = MODELS_DIR / LOCAL_MODEL_FILE

    def __init__(self):
        self._cancelled = False
        self._active = False

    def model_exists(self) -> bool:
        """Check if the local model is already downloaded and structurally healthy."""
        from core.providers.local import LocalProvider
        return bool(LocalProvider.health().get("available", False))

    def model_size_mb(self) -> float:
        """Return model size in MB, 0 if not installed."""
        if not self.model_exists():
            return 0.0
        return self.EXPECTED_MODEL.stat().st_size / 1024 / 1024

    def cancel(self):
        """Request cancel of any in-progress download."""
        self._cancelled = True

    def run(
        self,
        progress_callback: Callable[[str, int, int], None] | None = None,
        complete_callback: Callable[[dict], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Run the install hook.

        Checks if model exists locally. If not, downloads from Ollama registry.
        Returns immediately with status dict.

        Args:
            progress_callback: Optional (label: str, downloaded: int, total: int)
            complete_callback: Optional (result: dict) called when download completes
            error_callback: Optional (error: str) called on failure

        Returns:
            Dict with status:
                {"status": "installed", "path": str, "size_mb": float}
                {"status": "downloading", "size_mb": float, "message": str}
                {"status": "error", "message": str}
                {"status": "not_available", "message": str}
        """
        self._cancelled = False
        self._active = True

        if self.model_exists():
            logger.info(f"Model already installed: {self.EXPECTED_MODEL} ({self.model_size_mb():.1f} MB)")
            return {
                "status": "installed",
                "path": str(self.EXPECTED_MODEL),
                "size_mb": round(self.model_size_mb(), 1),
            }

        # Check availability in registry
        from core.model_fetch.ollama_pull import check_model_available as _check

        logger.info("Checking Ollama registry for model...")
        available = _check("DBERT", "DBERT_AI", "latest")

        if not available.get("available"):
            msg = available.get("reason", "Unknown error")
            logger.error(f"Model not available: {msg}")
            if error_callback:
                error_callback(msg)
            return {"status": "not_available", "message": msg}

        # Start download in background
        logger.info(f"Starting download: {available['size_mb']} MB")
        if progress_callback:
            progress_callback("init", 0, available["size_mb"] * 1024 * 1024)

        t = threading.Thread(
            target=self._download_worker,
            args=(progress_callback, complete_callback, error_callback),
            daemon=True,
        )
        t.start()

        return {
            "status": "downloading",
            "size_mb": available["size_mb"],
            "message": f"Downloading DBERT_AI ({available['size_mb']} MB) from Ollama registry",
        }

    def _download_worker(
        self,
        progress_callback: Callable[[str, int, int], None] | None,
        complete_callback: Callable[[dict], None] | None,
        error_callback: Callable[[str], None] | None,
    ):
        """Background download worker."""
        try:
            from core.model_fetch.ollama_pull import OllamaPullError
            from core.model_fetch.ollama_pull import pull_model as _pull

            def _progress(label: str, downloaded: int, total: int):
                if self._cancelled:
                    raise OllamaPullError("Cancelled by user")
                if progress_callback:
                    progress_callback(label, downloaded, total)

            result = _pull(progress_callback=_progress)

            logger.info(f"Install complete: {result['path']} ({result['size_mb']} MB)")
            if complete_callback:
                complete_callback(result)

        except OllamaPullError as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="install_hook_download")
            logger.error(f"Install failed: {exc}")
            if error_callback:
                error_callback(sanitized.user_message)
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category="install_hook_download")
            logger.error(f"Install unexpected error: {exc}")
            if error_callback:
                error_callback(sanitized.user_message)
        finally:
            self._active = False


# Singleton
_install_hook: InstallHook | None = None


def get_install_hook() -> InstallHook:
    """Get the singleton install hook."""
    global _install_hook
    if _install_hook is None:
        _install_hook = InstallHook()
    return _install_hook
