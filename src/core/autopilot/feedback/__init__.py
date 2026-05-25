"""Re-exports for autopilot.feedback package."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List

from ._mixin_core import ClosedLoopFeedback
from ._types import FeedbackAction, FeedbackCycle

_closed_loop_feedback_instance: ClosedLoopFeedback | None = None
_closed_loop_feedback_lock = threading.Lock()


def get_closed_loop_feedback(
    db_path: str | None = None,
    max_cycles_without_improvement: int = 10,
) -> ClosedLoopFeedback:
    """Return the ClosedLoopFeedback singleton (thread-safe)."""
    global _closed_loop_feedback_instance
    if _closed_loop_feedback_instance is None:
        with _closed_loop_feedback_lock:
            if _closed_loop_feedback_instance is None:
                _closed_loop_feedback_instance = ClosedLoopFeedback(
                    db_path=db_path,
                    max_cycles_without_improvement=max_cycles_without_improvement,
                )
    return _closed_loop_feedback_instance


def reset_closed_loop_feedback() -> None:
    """Reset the singleton (mainly for testing)."""
    global _closed_loop_feedback_instance
    with _closed_loop_feedback_lock:
        _closed_loop_feedback_instance = None


__all__ = [
    "Any",
    "ClosedLoopFeedback",
    "Dict",
    "FeedbackAction",
    "FeedbackCycle",
    "List",
    "get_closed_loop_feedback",
    "json",
    "logging",
    "reset_closed_loop_feedback",
    "sqlite3",
    "time",
    "uuid",
]
