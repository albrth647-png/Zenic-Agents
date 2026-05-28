"""Re-exports for trigger_map package."""

import fnmatch
import json
import logging
import os
import sqlite3
import threading
import time
import uuid

from ._mixin_core import TriggerMap
from ._types import ConditionOperator, TriggerCondition, TriggerMapping

_instance: TriggerMap | None = None  # TODO: verify import
_instance_lock = threading.Lock()


def get_trigger_map() -> TriggerMap:  # TODO: verify import
    """Return the singleton TriggerMap instance."""  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = TriggerMap()  # TODO: Phase3 - verify import
    return _instance


def reset_trigger_map() -> None:
    """Reset the singleton (mainly for testing)."""
    global _instance
    with _instance_lock:
        _instance = None


__all__ = [
    "ConditionOperator",
    "TriggerCondition",
    "TriggerMap",
    "TriggerMapping",
    "fnmatch",
    "get_trigger_map",
    "json",
    "logging",
    "os",
    "reset_trigger_map",
    "sqlite3",
    "time",
    "uuid",
]  # TODO: verify import
