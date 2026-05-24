"""Re-exports for feedback package."""


import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

_closed_loop_feedback_instance: Optional[ClosedLoopFeedback] = None  # noqa: F821  # TODO: verify import
_closed_loop_feedback_lock = threading.Lock()


def get_closed_loop_feedback(
    db_path: str = "autopilot_feedback.sqlite",
    max_cycles_without_improvement: int = 3,
) -> ClosedLoopFeedback:  # noqa: F821  # TODO: verify import
    """Get or create the global ClosedLoopFeedback instance.  # noqa: F821  # TODO: verify import

    Args:
        db_path: Path to the SQLite database file.
        max_cycles_without_improvement: Max cycles without improvement before escalation.

    Returns:
        The singleton ClosedLoopFeedback instance.  # noqa: F821  # TODO: verify import
    """
    global _closed_loop_feedback_instance
    with _closed_loop_feedback_lock:
        if _closed_loop_feedback_instance is None:
            _closed_loop_feedback_instance = ClosedLoopFeedback(  # noqa: F821  # TODO: Phase3 - verify import
                db_path=db_path,
                max_cycles_without_improvement=max_cycles_without_improvement,
            )
        return _closed_loop_feedback_instance


def reset_closed_loop_feedback() -> None:
    """Reset the global ClosedLoopFeedback instance (for testing)."""  # noqa: F821  # TODO: verify import
    global _closed_loop_feedback_instance
    with _closed_loop_feedback_lock:
        _closed_loop_feedback_instance = None



__all__ = ["FeedbackAction", "FeedbackCycle", "ClosedLoopFeedback", "get_closed_loop_feedback", "reset_closed_loop_feedback", "json", "logging", "sqlite3", "time", "uuid", "Any", "Dict", "List"]  # noqa: F821  # TODO: verify import