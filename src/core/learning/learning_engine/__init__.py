"""Re-exports for learning_engine package."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set

__all__ = ["Any", "Dict", "List", "Set", "json", "logging", "sqlite3", "time", "uuid"]

_instance: LearningEngine | None = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()


def get_learning_engine() -> LearningEngine:  # noqa: F821  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = LearningEngine()  # noqa: F821  # TODO: Phase3 - verify import
    return _instance


def reset_learning_engine() -> None:
    global _instance
    with _instance_lock:
        _instance = None
