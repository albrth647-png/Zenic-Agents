"""Re-exports for engine package."""

import threading
from typing import Optional

_engine_instance: PolicyCodeEngine | None = None  # noqa: F821  # TODO: verify import
_engine_lock = threading.Lock()


def get_policy_code_engine(db_path: str | None = None) -> PolicyCodeEngine:  # noqa: F821  # TODO: verify import
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = PolicyCodeEngine(db_path=db_path)  # noqa: F821  # TODO: Phase3 - verify import
        return _engine_instance


def reset_policy_code_engine() -> None:
    global _engine_instance
    with _engine_lock:
        _engine_instance = None
