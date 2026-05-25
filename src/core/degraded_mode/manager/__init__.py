"""Re-exports for manager package."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any, Dict, List, Optional
from ._mixin_core import DegradedModeManager

__all__ = ["Callable", "Dict", "List", "Optional", "logging", "time"]

_lock = threading.Lock()


def get_degraded_mode_manager(**kwargs: Any) -> DegradedModeManager:  # noqa: F821  # TODO: verify import
    """Get or create the global DegradedModeManager instance."""  # TODO: verify import
    global _degraded_mode_manager
    with _lock:
        if _degraded_mode_manager is None:
            _degraded_mode_manager = DegradedModeManager(**kwargs)  # noqa: F821  # TODO: Phase3 - verify import
        return _degraded_mode_manager


def reset_degraded_mode_manager() -> None:
    """Reset the global DegradedModeManager (for testing)."""  # TODO: verify import
    global _degraded_mode_manager
    _degraded_mode_manager = None
