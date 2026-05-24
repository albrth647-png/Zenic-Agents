"""Re-exports for inter_workflow package."""


import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid

_instance: InterWorkflowHandoff | None = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()
def get_inter_workflow_handoff() -> InterWorkflowHandoff:  # noqa: F821  # TODO: verify import
    """Return the InterWorkflowHandoff singleton (thread-safe)."""  # noqa: F821  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = InterWorkflowHandoff()  # noqa: F821  # TODO: Phase3 - verify import
    return _instance



__all__ = ["HandoffRule", "HandoffResult", "FieldMapping", "InterWorkflowHandoff", "get_inter_workflow_handoff", "json", "logging", "os", "re", "sqlite3", "time", "uuid"]  # noqa: F821  # TODO: verify import