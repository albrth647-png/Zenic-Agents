"""Re-exports for engine package."""


import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set

__all__ = ["hashlib", "json", "logging", "sqlite3", "time", "uuid", "Any", "Dict", "List", "Set"]

_instance: Optional[MemoryEngineV2] = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()
def get_memory_engine_v2() -> MemoryEngineV2:  # noqa: F821  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = MemoryEngineV2()  # noqa: F821  # TODO: Phase3 - verify import
    return _instance


def reset_memory_engine_v2() -> None:
    global _instance
    with _instance_lock:
        _instance = None

