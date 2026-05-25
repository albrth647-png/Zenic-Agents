"""Re-exports for exceptions.engine package."""

import json
import logging
import sqlite3
import threading
import time
import uuid

from ._mixin_core import ExceptionEngine
from ._types import ExceptionRecord, ExceptionSignal

_engine_instance: ExceptionEngine | None = None
_engine_lock = threading.Lock()


def get_exception_engine() -> ExceptionEngine:
    """Return the ExceptionEngine singleton (thread-safe)."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = ExceptionEngine()
    return _engine_instance


def reset_exception_engine() -> None:
    """Reset the singleton (mainly for testing)."""
    global _engine_instance
    with _engine_lock:
        _engine_instance = None


__all__ = [
    "ExceptionEngine",
    "ExceptionRecord",
    "ExceptionSignal",
    "get_exception_engine",
    "json",
    "logging",
    "reset_exception_engine",
    "sqlite3",
    "time",
    "uuid",
]
