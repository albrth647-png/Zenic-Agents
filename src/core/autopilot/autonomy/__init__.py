"""Re-exports for autopilot.autonomy package."""

import threading

from ._mixin_core import AutonomyConfigManager
from ._types import AutonomyConfig, AutonomyLevel

_instance: AutonomyConfigManager | None = None
_lock = threading.Lock()


def get_autonomy_config() -> AutonomyConfigManager:
    """Return the AutonomyConfigManager singleton (thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AutonomyConfigManager()
    return _instance


def reset_autonomy_config() -> None:
    """Reset the singleton (mainly for testing)."""
    global _instance
    with _lock:
        _instance = None


__all__ = [
    "AutonomyConfig",
    "AutonomyConfigManager",
    "AutonomyLevel",
    "get_autonomy_config",
    "reset_autonomy_config",
]
