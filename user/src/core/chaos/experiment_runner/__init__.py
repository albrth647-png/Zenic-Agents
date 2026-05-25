"""Re-exports for experiment_runner package."""

import threading
from typing import Optional

from ._mixin_core import ChaosExperimentRunner

_runner_instance: ChaosExperimentRunner | None = None
_runner_lock = threading.Lock()


def get_chaos_runner(db_path: str | None = None) -> ChaosExperimentRunner:
    global _runner_instance
    with _runner_lock:
        if _runner_instance is None:
            _runner_instance = ChaosExperimentRunner(db_path=db_path)
        return _runner_instance


def reset_chaos_runner() -> None:
    global _runner_instance
    with _runner_lock:
        _runner_instance = None


__all__ = [
    "ChaosExperimentRunner",
    "get_chaos_runner",
    "reset_chaos_runner",
]
