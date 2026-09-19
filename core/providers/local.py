"""Gayatri AI — Local LLM provider using llama-cpp-python."""

from __future__ import annotations

import logging
import threading
import time

from collections.abc import Iterator

from core.config import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    LOCAL_MODEL_CONTEXT,
    LOCAL_MODEL_DIR,
    LOCAL_MODEL_FILE,
    LOCAL_MODEL_GPU_LAYERS,
)
from core.providers.base import (
    Capability,
    CatalogSource,
    ChatMessage,
    ChatOptions,
    ChatResponse,
    LLMProvider,
    ModelInfo,
    SpeedTier,
)

logger = logging.getLogger("gayatri.providers.local")

# Gemma 2 chat template tokens
_TURN_START = "<start_of_turn>"
_TURN_END = "<end_of_turn>"
_MODEL_TOKEN = "model"
_USER_TOKEN = "user"
_SYSTEM_TOKEN = "system"


class LocalModelError(Exception):
    """Raised when the local model fails to load or generate."""


def format_gemma_prompt(messages: list[dict]) -> str:
    """Format a list of chat messages into Gemma 2's chat template.

    Args:
        messages: List of {"role": "system|user|assistant", "content": str}

    Returns:
        Formatted prompt string ready for the model.
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"{_TURN_START}{_SYSTEM_TOKEN}\n{content}{_TURN_END}\n")
        elif role == "user":
            parts.append(f"{_TURN_START}{_USER_TOKEN}\n{content}{_TURN_END}\n")
        elif role == "assistant":
            parts.append(f"{_TURN_START}{_MODEL_TOKEN}\n{content}{_TURN_END}\n")
    # Always end with model turn so generation follows
    parts.append(f"{_TURN_START}{_MODEL_TOKEN}\n")
    return "".join(parts)


def format_chatml_prompt(messages: list[dict]) -> str:
    """Format a list of chat messages into ChatML template (Qwen2 / fine-tuned Gayatri).

    Args:
        messages: List of {"role": "system|user|assistant", "content": str}

    Returns:
        Formatted prompt string ready for ChatML-based models.
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


class LocalProvider:
    """Loads and runs a GGUF model via llama-cpp-python.

    Lazy-loads the model on first use. Singleton — load once, reuse.
    Thread-safe model loading and inference synchronization.
    """

    _model = None
    _model_lock = threading.Lock()
    _infer_lock = threading.Lock()
    _cancel_flag = False
    MODEL_PATH = LOCAL_MODEL_DIR / LOCAL_MODEL_FILE

    @classmethod
    def cancel(cls) -> None:
        """Flag the current generation to stop early."""
        logger.info("Cancellation requested for local model generation.")
        cls._cancel_flag = True

    @classmethod
    def _load_model(cls, **override_params):
        """Load the GGUF model. Called once.

        Auto-detects hardware if not explicitly overridden.
        Thread-safe singleton loading.
        """
        if cls._model is not None and not override_params:
            return cls._model

        with cls._model_lock:
            if cls._model is not None and not override_params:
                return cls._model

            try:
                from llama_cpp import Llama
            except ImportError:
                raise LocalModelError(
                    "llama-cpp-python not installed. Run: pip install llama-cpp-python"
                )

            model_path = cls.MODEL_PATH
            if not model_path.exists():
                raise LocalModelError(
                    f"Model not found at {model_path}. "
                    "Download the fine-tuned GGUF model first."
                )

            actual_size = model_path.stat().st_size
            if actual_size < 1024 * 1024:
                raise LocalModelError(
                    f"Model file at {model_path} is only {actual_size} bytes — "
                    "the download failed (likely a placeholder). Delete the file and "
                    "re-download via the app's Download button."
                )

            logger.info(f"Loading model: {model_path.name} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")
            start = time.time()

            # Use override params if provided, otherwise auto-detect
            if override_params:
                n_gpu_layers = override_params.get("n_gpu_layers", LOCAL_MODEL_GPU_LAYERS)
                n_ctx = override_params.get("n_ctx", LOCAL_MODEL_CONTEXT)
                n_threads = override_params.get("n_threads", 4)
            else:
                # Auto-detect hardware
                try:
                    from core.hardware import detect_hardware, recommend_llama_params
                    profile = detect_hardware()
                    model_size_mb = int(model_path.stat().st_size / (1024 * 1024))
                    params = recommend_llama_params(profile, model_size_mb)
                    n_gpu_layers = params.n_gpu_layers
                    n_ctx = params.n_ctx
                    n_threads = params.n_threads
                    logger.info(
                        f"Auto-detected: GPU={profile.gpu_name} "
                        f"(layers={n_gpu_layers}, ctx={n_ctx}, threads={n_threads})"
                    )
                except Exception as exc:
                    logger.warning(f"Hardware detection failed, using defaults: {exc}")
                    n_gpu_layers = LOCAL_MODEL_GPU_LAYERS
                    n_ctx = LOCAL_MODEL_CONTEXT
                    n_threads = 4

            try:
                cls._model = Llama(
                    model_path=str(model_path),
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                    verbose=False,
                    n_threads=n_threads,
                )
                # Attach KV RAM Cache to significantly reduce TTFT on repeated prefixes
                try:
                    try:
                        from llama_cpp import LlamaRAMCache
                        cache = LlamaRAMCache(capacity_bytes=512 * 1024 * 1024)  # 512MB cache
                        cls._model.set_cache(cache)
                        logger.info("Initialized 512MB LlamaRAMCache for prompt caching.")
                    except ImportError:
                        from llama_cpp import LlamaCache
                        cache = LlamaCache(capacity_bytes=512 * 1024 * 1024)
                        cls._model.set_cache(cache)
                        logger.info("Initialized 512MB LlamaCache for prompt caching.")
                except ImportError:
                    logger.info("Prompt caching disabled: neither LlamaRAMCache nor LlamaCache found in llama_cpp.")
            except Exception as exc:
                raise LocalModelError(f"Failed to load GGUF model: {exc}") from exc

            elapsed = time.time() - start
            logger.info(f"Model loaded in {elapsed:.1f}s (layers={n_gpu_layers}, ctx={n_ctx})")
            return cls._model

    @classmethod
    def health(cls) -> dict:
        """Return structured health status of the local model without forcing heavy model load."""
        model_path = cls.MODEL_PATH
        part_path = model_path.with_name(model_path.name + ".part")

        if not model_path.exists():
            if part_path.exists():
                part_size_mb = part_path.stat().st_size / (1024 * 1024)
                return {
                    "available": False,
                    "reason_code": "download_incomplete",
                    "message": f"Model download is incomplete ({part_size_mb:.1f} MB partial file found). Please resume or complete download.",
                    "path": str(model_path)
                }
            return {
                "available": False,
                "reason_code": "missing_file",
                "message": "Model file not found. Please download it.",
                "path": str(model_path)
            }

        actual_size = model_path.stat().st_size
        if actual_size < 1024 * 1024:
            return {
                "available": False,
                "reason_code": "invalid_file",
                "message": f"Model file is only {actual_size} bytes, likely a failed download.",
                "path": str(model_path)
            }

        # Check installation metadata if present for fast structural verification (Audit #41 & #44)
        try:
            from core.model_fetch.ollama_pull import get_model_metadata
            meta = get_model_metadata(dest_dir=model_path.parent, model_file=model_path.name)
            if meta and meta.get("size_bytes"):
                expected_bytes = meta["size_bytes"]
                if actual_size != expected_bytes:
                    return {
                        "available": False,
                        "reason_code": "corrupt_file",
                        "message": f"Model file size ({actual_size} bytes) does not match verified installation metadata ({expected_bytes} bytes).",
                        "path": str(model_path)
                    }
        except Exception:
            logger.debug("Model metadata check skipped (non-critical)", exc_info=True)

        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return {
                "available": False,
                "reason_code": "missing_dependency",
                "message": "llama-cpp-python not installed. Run: pip install llama-cpp-python",
                "path": str(model_path)
            }

        if cls._model is not None:
            return {
                "available": True,
                "reason_code": "ok",
                "message": "Model is loaded and ready.",
                "path": str(model_path)
            }

        return {
            "available": True,
            "reason_code": "ok",
            "message": "Model file ready to load.",
            "path": str(model_path)
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check if the model file exists and is ready to load."""
        return cls.health()["available"]

    @classmethod
    def stream(cls, prompt: str, **kwargs):
        """Stream tokens from the model. Yields strings."""
        model = cls._load_model()  # Evaluated eagerly
        max_tokens = kwargs.get("max_tokens", DEFAULT_MAX_TOKENS)
        temperature = kwargs.get("temperature", DEFAULT_TEMPERATURE)
        top_p = kwargs.get("top_p", DEFAULT_TOP_P)
        top_k = kwargs.get("top_k", DEFAULT_TOP_K)
        stop = kwargs.get("stop")
        if not stop:
            stop = ["<|im_end|>", "<|endoftext|>", "<end_of_turn>"]

        logger.info(f"Generating: max_tokens={max_tokens}, temp={temperature}")

        def _generator():
            try:
                import time
                start_time = time.time()
                first_token_time = None
                tokens_emitted = 0

                with cls._infer_lock:
                    cls._cancel_flag = False
                    stream_obj = model.create_completion(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        stop=stop,
                        stream=True,
                    )
                    for chunk in stream_obj:
                        if cls._cancel_flag:
                            logger.info("Local model generation cancelled by user.")
                            break
                        
                        text = chunk["choices"][0].get("text", "")
                        if text:
                            if first_token_time is None:
                                first_token_time = time.time()
                            tokens_emitted += 1
                            yield text

                    duration = time.time() - (first_token_time or start_time)
                    ttft = ((first_token_time or start_time) - start_time) * 1000
                    tps = tokens_emitted / duration if duration > 0 else 0
                    logger.info(
                        f"TELEMETRY: {{\"ttft_ms\": {ttft:.1f}, "
                        f"\"generation_ms\": {duration*1000:.1f}, "
                        f"\"output_tokens\": {tokens_emitted}, "
                        f"\"tokens_per_second\": {tps:.1f}}}"
                    )
                    cls._cancel_flag = False
            except Exception as exc:
                logger.error(f"Generation failed: {exc}")
                raise LocalModelError(f"Generation failed: {exc}") from exc
                
        return _generator()

    @classmethod
    def chat_stream(cls, messages: list[dict], **kwargs):
        """Stream a response from a list of chat messages using native model chat template.

        Uses model.create_chat_completion to automatically apply the GGUF model's
        embedded Jinja chat template (supporting ChatML for Qwen2, Gemma, etc.).

        Args:
            messages: List of {"role": "system|user|assistant", "content": str}
            **kwargs: Generation parameters (max_tokens, temperature, etc.)

        Yields:
            Token strings.
        """
        model = cls._load_model()
        max_tokens = kwargs.get("max_tokens", DEFAULT_MAX_TOKENS)
        temperature = kwargs.get("temperature", DEFAULT_TEMPERATURE)
        top_p = kwargs.get("top_p", DEFAULT_TOP_P)
        top_k = kwargs.get("top_k", DEFAULT_TOP_K)
        stop = kwargs.get("stop")
        if not stop:
            stop = ["<|im_end|>", "<|endoftext|>", "<end_of_turn>"]

        logger.info(f"Chat generating: max_tokens={max_tokens}, temp={temperature}")

        def _chat_generator():
            try:
                import time
                start_time = time.time()
                first_token_time = None
                tokens_emitted = 0

                with cls._infer_lock:
                    cls._cancel_flag = False
                    try:
                        stream_obj = model.create_chat_completion(
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            top_k=top_k,
                            stop=stop,
                            stream=True,
                        )
                        for chunk in stream_obj:
                            if cls._cancel_flag:
                                logger.info("Local model generation cancelled by user.")
                                break

                            delta = chunk["choices"][0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                tokens_emitted += 1
                                yield text
                    except Exception as chat_exc:
                        logger.warning(
                            f"create_chat_completion failed ({chat_exc}), falling back to prompt completion"
                        )
                        prompt = format_chatml_prompt(messages)
                        comp_stream = model.create_completion(
                            prompt=prompt,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            top_k=top_k,
                            stop=stop,
                            stream=True,
                        )
                        for chunk in comp_stream:
                            if cls._cancel_flag:
                                logger.info("Local model generation cancelled by user.")
                                break
                            text = chunk["choices"][0].get("text", "")
                            if text:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                tokens_emitted += 1
                                yield text

                    duration = time.time() - (first_token_time or start_time)
                    ttft = ((first_token_time or start_time) - start_time) * 1000
                    tps = tokens_emitted / duration if duration > 0 else 0
                    logger.info(
                        f"TELEMETRY: {{\"ttft_ms\": {ttft:.1f}, "
                        f"\"generation_ms\": {duration*1000:.1f}, "
                        f"\"output_tokens\": {tokens_emitted}, "
                        f"\"tokens_per_second\": {tps:.1f}}}"
                    )
                    cls._cancel_flag = False
            except Exception as exc:
                logger.error(f"Chat generation failed: {exc}")
                raise LocalModelError(f"Chat generation failed: {exc}") from exc

        return _chat_generator()

    @classmethod
    def chat(cls, messages: list[dict], **kwargs) -> str:
        """Generate a response from a list of chat messages.

        Args:
            messages: List of {"role": "system|user|assistant", "content": str}
            **kwargs: Generation parameters (max_tokens, temperature, etc.)

        Returns:
            Full response string.
        """
        tokens = list(cls.chat_stream(messages, **kwargs))
        return "".join(tokens)

    @classmethod
    def generate(cls, prompt: str, **kwargs) -> str:
        """Non-streaming generation. Returns the full response."""
        tokens = list(cls.stream(prompt, **kwargs))
        return "".join(tokens)

    @classmethod
    def reset(cls):
        """Unload the model (for testing or reload)."""
        with cls._model_lock:
            cls._model = None


class LocalLLMProvider(LLMProvider):
    """Adapter exposing LocalProvider (GGUF via llama-cpp-python) as an LLMProvider."""

    def __init__(self):
        self._name = "Local (GGUF)"
        self._key = "local"
        self._models: list[ModelInfo] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        return self._key

    @property
    def is_local(self) -> bool:
        return True

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_reachable(self) -> bool:
        return True

    def is_ready(self) -> bool:
        return LocalProvider.is_available()

    def validate_key(self) -> tuple[bool, str]:
        if LocalProvider.is_available():
            return True, "OK"
        return False, "Local model file not installed"

    def list_models(self) -> list[ModelInfo]:
        from core.config import LOCAL_MODEL_FILE
        is_avail = LocalProvider.is_available()
        return [
            ModelInfo(
                id="local",
                name=f"Local Model ({LOCAL_MODEL_FILE})",
                provider="local",
                context_length=8192,
                speed_tier=SpeedTier.SLOW,
                capabilities=[Capability.CHAT, Capability.STREAM, Capability.SYSTEM_PROMPT],
                supports_tools=False,
                supports_vision=False,
                supports_json=False,
                catalog_source=CatalogSource.LIVE if is_avail else CatalogSource.FALLBACK,
            )
        ]

    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        opts = options or ChatOptions()
        start = time.time()
        dict_msgs = [m.to_dict() for m in messages]
        text = LocalProvider.chat(
            dict_msgs,
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            top_p=opts.top_p,
            top_k=opts.top_k,
            stop=opts.stop or None,
        )
        latency = (time.time() - start) * 1000
        return ChatResponse(
            text=text,
            model_id="local",
            provider="local",
            tokens_used=len(text) // 4,
            latency_ms=round(latency, 1),
        )

    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        opts = options or ChatOptions()
        dict_msgs = [m.to_dict() for m in messages]
        yield from LocalProvider.chat_stream(
            dict_msgs,
            max_tokens=opts.max_tokens,
            temperature=opts.temperature,
            top_p=opts.top_p,
            top_k=opts.top_k,
            stop=opts.stop or None,
        )
