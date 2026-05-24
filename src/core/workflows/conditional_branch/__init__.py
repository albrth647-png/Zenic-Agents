"""Re-exports for conditional_branch package."""

import logging
import re
import threading
import time
import uuid

_instance: ConditionalBranching | None = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()


def get_conditional_branching() -> ConditionalBranching:  # noqa: F821  # TODO: verify import
    """Return the ConditionalBranching singleton (thread-safe)."""  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ConditionalBranching()  # noqa: F821  # TODO: Phase3 - verify import
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
]  # TODO: verify import
