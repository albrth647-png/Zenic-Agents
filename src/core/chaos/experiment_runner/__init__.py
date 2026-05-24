"""Re-exports for experiment_runner package."""

import threading
from typing import Optional

_runner_instance: ChaosExperimentRunner | None = None  # noqa: F821  # TODO: verify import
_runner_lock = threading.Lock()


def get_chaos_runner(db_path: str | None = None) -> ChaosExperimentRunner:  # noqa: F821  # TODO: verify import
    global _runner_instance
    with _runner_lock:
        if _runner_instance is None:
            _runner_instance = ChaosExperimentRunner(db_path=db_path)  # noqa: F821  # TODO: Phase3 - verify import
        return _runner_instance


def reset_chaos_runner() -> None:
    global _runner_instance
    with _runner_lock:
        _runner_instance = None
