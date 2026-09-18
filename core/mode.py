from enum import Enum
from dataclasses import dataclass

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

def get_mode_policy(mode: AppMode | str) -> ModePolicy:
    try:
        if isinstance(mode, str):
            mode = AppMode(mode)
        return _POLICIES[mode]
    except ValueError:
        raise ValueError(f"Unknown mode: {mode}")
