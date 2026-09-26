"""Gayatri AI — Application Mode Policy & Server-Side Mode Validation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvalidAppModeError(ValueError):
    """Raised when an unrecognized mode is passed to backend entrypoints."""
    pass


class AppMode(str, Enum):
    CHEMISTRY_TUTOR = "chemistry_tutor"
    GENERAL_ASSISTANT = "general_assistant"


@dataclass
class ModePolicy:
    chemistry_only: bool
    rag: bool
    assessment: bool
    adaptive_learning: bool
    controlled_web_fallback: bool


_POLICIES = {
    AppMode.CHEMISTRY_TUTOR: ModePolicy(
        chemistry_only=True,
        rag=True,
        assessment=True,
        adaptive_learning=True,
        controlled_web_fallback=True
    ),
    AppMode.GENERAL_ASSISTANT: ModePolicy(
        chemistry_only=False,
        rag=False,
        assessment=False,
        adaptive_learning=False,
        controlled_web_fallback=False
    )
}


def validate_app_mode(mode: AppMode | str) -> AppMode:
    """Validate server-side mode parameter. Raises InvalidAppModeError if invalid."""
    if isinstance(mode, AppMode):
        return mode
    try:
        return AppMode(str(mode).lower().strip())
    except ValueError:
        raise InvalidAppModeError(
            f"Invalid mode '{mode}'. Supported modes are: "
            f"{[m.value for m in AppMode]}"
        )


def get_mode_policy(mode: AppMode | str) -> ModePolicy:
    app_mode = validate_app_mode(mode)
    return _POLICIES[app_mode]
