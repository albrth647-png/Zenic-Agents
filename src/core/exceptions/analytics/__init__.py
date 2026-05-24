"""Re-exports for analytics package."""


import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

_analytics_instance: Optional[ExceptionAnalytics] = None  # noqa: F821  # TODO: verify import
_analytics_lock = threading.Lock()


def get_exception_analytics(
    db_path: str = "exception_analytics.sqlite",
) -> ExceptionAnalytics:  # noqa: F821  # TODO: verify import
    """Get or create the global ExceptionAnalytics instance.  # noqa: F821  # TODO: verify import

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The singleton ExceptionAnalytics instance.  # noqa: F821  # TODO: verify import
    """
    global _analytics_instance
    with _analytics_lock:
        if _analytics_instance is None:
            _analytics_instance = ExceptionAnalytics(db_path=db_path)  # noqa: F821  # TODO: Phase3 - verify import
        return _analytics_instance


def reset_exception_analytics() -> None:
    """Reset the global :class:`ExceptionAnalytics` (for testing)."""  # noqa: F821  # TODO: verify import
    global _analytics_instance
    with _analytics_lock:
        _analytics_instance = None


__all__ = ["ExceptionPattern", "AnalyticsSnapshot", "ExceptionAnalytics", "get_exception_analytics", "reset_exception_analytics", "json", "logging", "sqlite3", "time", "uuid", "Any", "Callable", "Dict", "List", "Tuple"]  # noqa: F821  # TODO: verify import