"""Helper methods extracted from chain."""

from __future__ import annotations


import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)



# ── Singleton ─────────────────────────────────────────────

_approval_chain_instance: Optional[ApprovalChain] = None  # noqa: F821  # TODO: verify import
_approval_chain_lock = threading.Lock()


def get_approval_chain(db_path: str = "approval_chain.sqlite") -> ApprovalChain:  # noqa: F821  # TODO: verify import
    """Get or create the global ApprovalChain instance."""  # noqa: F821  # TODO: verify import
    global _approval_chain_instance
    with _approval_chain_lock:
        if _approval_chain_instance is None:
            _approval_chain_instance = ApprovalChain(db_path=db_path)  # noqa: F821  # TODO: Phase3 - verify import
        return _approval_chain_instance


def reset_approval_chain() -> None:
    """Reset the global ApprovalChain (for testing)."""  # noqa: F821  # TODO: verify import
    global _approval_chain_instance
    _approval_chain_instance = None
__all__ = ["_approval_chain_instance", "_approval_chain_lock", "get_approval_chain", "logger", "reset_approval_chain"]
