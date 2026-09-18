"""Gayatri AI — Settings persistence.

Validated settings.json for app configuration.
Read/write with schema validation.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from core.config import SETTINGS_PATH

logger = logging.getLogger("gayatri.settings")

# Schema: key → expected type
_SETTINGS_SCHEMA: dict[str, type] = {
    "theme": str,           # "dark" | "light"
    "local_model_installed": bool,
    "local_model_path": str,
    "providers": dict,      # {provider_key: {enabled, api_key_ref, ...}}
    "router_preference": str,  # "balanced" | "quality" | "cheap" | "local_only"
    "privacy_mode": str,    # "local_only" | "cloud_allowed"
    "first_run_complete": bool,
    "telemetry_enabled": bool,
    "auto_download_model": bool,
    "max_tokens": int,
    "temperature": float,
    "system_prompt": str,
    "agent.max_steps": int,
    "agent.time_budget_s": float,
}

# Semantic Range & Allowed Value Constants (Audit #27)
ALLOWED_THEMES = frozenset({"dark", "light"})
ALLOWED_ROUTER_PREFERENCES = frozenset({"balanced", "quality", "cheap", "local_only"})
ALLOWED_PRIVACY_MODES = frozenset({"local_only", "cloud_allowed"})
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_MAX_TOKENS = 1
MAX_MAX_TOKENS = 32768
MAX_SYSTEM_PROMPT_LEN = 10000

# Defaults
_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "local_model_installed": False,
    "local_model_path": "",
    "providers": {},
    "router_preference": "balanced",
    "privacy_mode": "local_only",  # Default: no data leaves device
    "first_run_complete": False,
    "telemetry_enabled": False,
    "auto_download_model": True,
    "max_tokens": 512,
    "temperature": 0.7,
    "system_prompt": "You are Gayatri AI, a helpful learning assistant.",
}


def validate_setting(key: str, value: Any) -> Any:
    """Validate a setting key and its value against the schema and semantic ranges.

    Returns the sanitized / normalized value if valid.
    Raises KeyError if key is unknown.
    Raises ValueError or TypeError if the value violates type or range constraints.
    """
    if key not in _SETTINGS_SCHEMA:
        raise KeyError(
            f"Unknown setting key: '{key}'. Valid keys are: {sorted(_SETTINGS_SCHEMA.keys())}"
        )

    if value is None:
        raise ValueError(f"Setting '{key}' cannot be None")

    expected_type = _SETTINGS_SCHEMA[key]

    # Strict type checks (Audit #27)
    if expected_type is bool:
        if not isinstance(value, bool):
            raise ValueError(f"Setting '{key}' must be bool, got {type(value).__name__}")
        return value

    if expected_type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Setting '{key}' must be int, got {type(value).__name__}")
        if key == "max_tokens" and not (MIN_MAX_TOKENS <= value <= MAX_MAX_TOKENS):
            raise ValueError(
                f"Setting 'max_tokens' must be between {MIN_MAX_TOKENS} and {MAX_MAX_TOKENS}, got {value}"
            )
        return value

    if expected_type is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Setting '{key}' must be float, got {type(value).__name__}")
        val_float = float(value)
        if key == "temperature" and not (MIN_TEMPERATURE <= val_float <= MAX_TEMPERATURE):
            raise ValueError(
                f"Setting 'temperature' must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}, got {val_float}"
            )
        return val_float

    if expected_type is str:
        if not isinstance(value, str):
            raise ValueError(f"Setting '{key}' must be str, got {type(value).__name__}")
        if key == "theme" and value not in ALLOWED_THEMES:
            raise ValueError(
                f"Setting 'theme' must be one of {sorted(ALLOWED_THEMES)}, got {value!r}"
            )
        if key == "router_preference" and value not in ALLOWED_ROUTER_PREFERENCES:
            raise ValueError(
                f"Setting 'router_preference' must be one of {sorted(ALLOWED_ROUTER_PREFERENCES)}, got {value!r}"
            )
        if key == "privacy_mode" and value not in ALLOWED_PRIVACY_MODES:
            raise ValueError(
                f"Setting 'privacy_mode' must be one of {sorted(ALLOWED_PRIVACY_MODES)}, got {value!r}"
            )
        if key == "system_prompt":
            if not value.strip():
                raise ValueError("Setting 'system_prompt' cannot be empty or whitespace only")
            if len(value) > MAX_SYSTEM_PROMPT_LEN:
                raise ValueError(
                    f"Setting 'system_prompt' exceeds max length of {MAX_SYSTEM_PROMPT_LEN} characters"
                )
        return value

    if expected_type is dict:
        if not isinstance(value, dict):
            raise ValueError(f"Setting '{key}' must be dict, got {type(value).__name__}")
        return value

    return value


class SettingsStore:
    """Thread-safe settings persistence.

    Reads/writes a JSON file with validation.
    """

    def __init__(self, settings_path: str | Path | None = None):
        self._path = Path(settings_path) if settings_path else SETTINGS_PATH
        self._lock = threading.RLock()
        self._settings: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load settings from disk with UTF-8 encoding and schema validation."""
        with self._lock:
            if self._path.exists():
                try:
                    with open(self._path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    self._settings = {}
                    for key, val in raw_data.items():
                        try:
                            self._settings[key] = validate_setting(key, val)
                        except (KeyError, ValueError, TypeError) as val_err:
                            logger.warning(
                                f"Invalid setting in {self._path} for '{key}': {val_err}. "
                                "Falling back to default or discarding."
                            )
                            if key in _DEFAULTS:
                                self._settings[key] = _DEFAULTS[key]

                    # Apply any missing defaults
                    for key, default in _DEFAULTS.items():
                        if key not in self._settings:
                            self._settings[key] = default

                    logger.info(f"Settings loaded from {self._path}")
                except Exception as exc:
                    logger.error(f"Failed to load settings from {self._path}: {exc}")
                    self._settings = dict(_DEFAULTS)
            else:
                self._settings = dict(_DEFAULTS)
                self._save()

    def _save(self) -> None:
        """Save settings to disk with explicit UTF-8 encoding and atomic replace."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2, ensure_ascii=False)
        tmp_path.replace(self._path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value with strict semantic and type validation."""
        validated_val = validate_setting(key, value)
        with self._lock:
            self._settings[key] = validated_val
            self._save()
            logger.debug(f"Setting: {key} = {validated_val!r}")

    def get_all(self) -> dict[str, Any]:
        """Get all settings."""
        with self._lock:
            return dict(self._settings)

    def update(self, updates: dict[str, Any]) -> None:
        """Update multiple settings atomically after full validation."""
        validated_updates: dict[str, Any] = {}
        for key, value in updates.items():
            validated_updates[key] = validate_setting(key, value)

        with self._lock:
            self._settings.update(validated_updates)
            self._save()

    def reset(self) -> None:
        """Reset all settings to defaults."""
        with self._lock:
            self._settings = dict(_DEFAULTS)
            self._save()
            logger.info("Settings reset to defaults")


# Global instance
_settings: SettingsStore | None = None


def get_settings() -> SettingsStore:
    """Get the global settings store."""
    global _settings
    if _settings is None:
        _settings = SettingsStore()
    return _settings
