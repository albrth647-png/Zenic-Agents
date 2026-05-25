"""Re-exports for engine package."""

import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from ._mixin_core import MemoryEngineV2

_instance: MemoryEngineV2 | None = None
_instance_lock = threading.Lock()


def get_memory_engine_v2() -> MemoryEngineV2:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = MemoryEngineV2()
    return _instance


def reset_memory_engine_v2() -> None:
    global _instance
    with _instance_lock:
        _instance = None


__all__ = [
    "MemoryEngineV2",
    "get_memory_engine_v2",
    "reset_memory_engine_v2",
]
