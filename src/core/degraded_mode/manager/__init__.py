"""Re-exports for manager package."""


import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

__all__ = ["logging", "time", "Callable", "Dict", "List", "Optional"]

_lock = threading.Lock()
def get_degraded_mode_manager(**kwargs: Any) -> DegradedModeManager:  # noqa: F821  # TODO: verify import
    """Get or create the global DegradedModeManager instance."""  # noqa: F821  # TODO: verify import
    global _degraded_mode_manager
    with _lock:
        if _degraded_mode_manager is None:
            _degraded_mode_manager = DegradedModeManager(**kwargs)  # noqa: F821  # TODO: Phase3 - verify import
        return _degraded_mode_manager


def reset_degraded_mode_manager() -> None:
    """Reset the global DegradedModeManager (for testing)."""  # noqa: F821  # TODO: verify import
    global _degraded_mode_manager
    _degraded_mode_manager = None

