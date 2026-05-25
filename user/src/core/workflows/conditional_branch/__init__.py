"""Re-exports for conditional_branch package."""

import logging
import re
import threading
import time
import uuid

from ._mixin_core import ConditionalBranching
from ._types import BranchCondition, BranchRule
from ._helpers import safe_evaluate

_instance: ConditionalBranching | None = None
_instance_lock = threading.Lock()


def get_conditional_branching() -> ConditionalBranching:
    """Return the ConditionalBranching singleton (thread-safe)."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ConditionalBranching()
    return _instance


__all__ = [
    "BranchCondition",
    "BranchRule",
    "ConditionalBranching",
    "get_conditional_branching",
    "logging",
    "re",
    "safe_evaluate",
    "time",
    "uuid",
]
