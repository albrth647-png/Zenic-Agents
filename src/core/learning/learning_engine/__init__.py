"""Re-exports for learning_engine package."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from ._mixin_core import LearningEngine
from ._types import LearningInsight, LearningStrategy
from ._helpers import _new_id, _now_iso, _retry

_instance: LearningEngine | None = None
_instance_lock = threading.Lock()


def get_learning_engine() -> LearningEngine:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = LearningEngine()
    return _instance


def reset_learning_engine() -> None:
    global _instance
    with _instance_lock:
        _instance = None


__all__ = [
    "LearningEngine",
    "LearningInsight",
    "LearningStrategy",
    "_new_id",
    "_now_iso",
    "_retry",
    "get_learning_engine",
    "reset_learning_engine",
]
