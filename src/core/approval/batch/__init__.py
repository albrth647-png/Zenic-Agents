"""
Zenic-Agents Asistente - Batch Approval Engine (Phase C3)

Approve or reject multiple similar actions at once. A batch groups
identical-type approval requests so that an approver can act on all
of them in a single operation, with optional partial approval support.
"""

# ── Singleton ─────────────────────────────────────────────
import threading
from typing import Optional

from ._mixin_core import BatchApprovalEngine
from ._types import _MAX_RETRIES, _RETRY_DELAY, BatchRequest, BatchResult

_batch_instance: BatchApprovalEngine | None = None
_batch_lock = threading.Lock()


def get_batch_approval(db_path: str = "batch_approval.sqlite") -> BatchApprovalEngine:
    """Get or create the global BatchApprovalEngine instance."""
    global _batch_instance
    with _batch_lock:
        if _batch_instance is None:
            _batch_instance = BatchApprovalEngine(db_path=db_path)
        return _batch_instance


def reset_batch_approval() -> None:
    """Reset the global BatchApprovalEngine (for testing)."""
    global _batch_instance
    _batch_instance = None


__all__ = [
    "_MAX_RETRIES",
    "_RETRY_DELAY",
    "BatchApprovalEngine",
    "BatchRequest",
    "BatchResult",
    "get_batch_approval",
    "reset_batch_approval",
]
