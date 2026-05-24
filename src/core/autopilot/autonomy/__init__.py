"""Re-exports for autonomy package."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

_autonomy_config_instance: AutonomyConfigManager | None = None  # noqa: F821  # TODO: verify import
_autonomy_config_lock = threading.Lock()


def get_autonomy_config(db_path: str = "autonomy_config.sqlite") -> AutonomyConfigManager:  # noqa: F821  # TODO: verify import
    """Get or create the global AutonomyConfigManager instance.  # noqa: F821  # TODO: verify import

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The singleton AutonomyConfigManager instance.  # noqa: F821  # TODO: verify import
    """
    global _autonomy_config_instance
    with _autonomy_config_lock:
        if _autonomy_config_instance is None:
            _autonomy_config_instance = AutonomyConfigManager(db_path=db_path)  # noqa: F821  # TODO: Phase3 - verify import
        return _autonomy_config_instance


def reset_autonomy_config() -> None:
    """Reset the global AutonomyConfigManager instance (for testing)."""  # TODO: verify import
    global _autonomy_config_instance
    with _autonomy_config_lock:
        _autonomy_config_instance = None


__all__ = [
    "Any",
    "AutonomyConfig",
    "AutonomyConfigManager",
    "AutonomyLevel",
    "Dict",
    "List",
    "get_autonomy_config",
    "json",
    "logging",
    "reset_autonomy_config",
    "sqlite3",
    "time",
    "uuid",
]  # TODO: verify import
