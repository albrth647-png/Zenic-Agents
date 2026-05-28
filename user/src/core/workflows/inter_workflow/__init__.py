"""Re-exports for inter_workflow package."""

import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid

from ._mixin_core import InterWorkflowHandoff
from ._types import FieldMapping, HandoffResult, HandoffRule

_instance: InterWorkflowHandoff | None = None  # TODO: verify import
_instance_lock = threading.Lock()


def get_inter_workflow_handoff() -> InterWorkflowHandoff:  # TODO: verify import
    """Return the InterWorkflowHandoff singleton (thread-safe)."""  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = InterWorkflowHandoff()  # TODO: Phase3 - verify import
    return _instance


__all__ = [
    "FieldMapping",
    "HandoffResult",
    "HandoffRule",
    "InterWorkflowHandoff",
    "get_inter_workflow_handoff",
    "json",
    "logging",
    "os",
    "re",
    "sqlite3",
    "time",
    "uuid",
]  # TODO: verify import
