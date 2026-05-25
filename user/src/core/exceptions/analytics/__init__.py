"""Re-exports for exceptions.analytics package."""

import logging
import threading
import time
import uuid

from ._mixin_core import ExceptionAnalytics
from ._types import AnalyticsSnapshot, ExceptionPattern

_analytics_instance: ExceptionAnalytics | None = None
_analytics_lock = threading.Lock()


def get_exception_analytics() -> ExceptionAnalytics:
    """Return the ExceptionAnalytics singleton (thread-safe)."""
    global _analytics_instance
    if _analytics_instance is None:
        with _analytics_lock:
            if _analytics_instance is None:
                _analytics_instance = ExceptionAnalytics()
    return _analytics_instance


def reset_exception_analytics() -> None:
    """Reset the singleton (mainly for testing)."""
    global _analytics_instance
    with _analytics_lock:
        _analytics_instance = None


__all__ = [
    "AnalyticsSnapshot",
    "ExceptionAnalytics",
    "ExceptionPattern",
    "get_exception_analytics",
    "logging",
    "reset_exception_analytics",
    "time",
    "uuid",
]
