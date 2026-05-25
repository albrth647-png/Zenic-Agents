"""Re-exports for engine package."""

import threading
from typing import Optional

from ._mixin_core import PolicyCodeEngine
from ._types import PolicyEvaluationResult

_engine_instance: PolicyCodeEngine | None = None
_engine_lock = threading.Lock()


def get_policy_code_engine(db_path: str | None = None) -> PolicyCodeEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = PolicyCodeEngine(db_path=db_path)
        return _engine_instance


def reset_policy_code_engine() -> None:
    global _engine_instance
    with _engine_lock:
        _engine_instance = None


__all__ = [
    "PolicyCodeEngine",
    "PolicyEvaluationResult",
    "get_policy_code_engine",
    "reset_policy_code_engine",
]
