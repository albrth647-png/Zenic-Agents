"""Re-exports for trigger_map package."""


import fnmatch
import json
import logging
import os
import sqlite3
import threading
import time
import uuid

_instance: TriggerMap | None = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()
def get_trigger_map() -> TriggerMap:  # noqa: F821  # TODO: verify import
    """Return the singleton TriggerMap instance."""  # noqa: F821  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = TriggerMap()  # noqa: F821  # TODO: Phase3 - verify import
    return _instance


def reset_trigger_map() -> None:
    """Reset the singleton (mainly for testing)."""
    global _instance
    with _instance_lock:
        _instance = None



__all__ = ["TriggerMap", "TriggerMapping", "TriggerCondition", "ConditionOperator", "get_trigger_map", "reset_trigger_map", "fnmatch", "json", "logging", "os", "sqlite3", "time", "uuid"]  # noqa: F821  # TODO: verify import