import threading
from dataclasses import dataclass


@dataclass
class AgentPolicy:
    max_steps: int = 12
    time_budget_s: float = 60.0
    tool_budget: int = 20
    token_budget: int | None = None

class CancelledError(Exception):
    """Raised when a cooperative tool is cancelled."""

class CancellationToken:
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

_local = threading.local()

def get_cancellation_token() -> CancellationToken | None:
    return getattr(_local, "token", None)

def set_cancellation_token(token: CancellationToken | None) -> None:
    _local.token = token

def check_cancelled():
    token = get_cancellation_token()
    if token and token.is_cancelled:
        raise CancelledError("Tool execution was cancelled due to timeout.")

def cooperative_tool(func):
    """Decorator to mark tools that participate in cooperative cancellation."""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        check_cancelled()
        return func(*args, **kwargs)
    return wrapper
