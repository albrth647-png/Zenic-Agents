"""
Zenic-Agents Asistente - Delegation Manager (Phase C3)

Handles approver substitution when the primary approver is unavailable.
Supports explicit delegation rules, automatic delegation, role hierarchy
verification, and acknowledgement tracking.
"""

# ── Singleton ─────────────────────────────────────────────
import threading
from typing import Optional

from ._mixin_core import DelegationManager
from ._types import _MAX_RETRIES, _RETRY_DELAY, DelegationRecord, DelegationRule

_delegation_instance: DelegationManager | None = None
_delegation_lock = threading.Lock()


def get_delegation_manager(
    db_path: str = "delegation.sqlite",
    default_timeout_hours: int = 24,
) -> DelegationManager:
    """Get or create the global DelegationManager instance."""
    global _delegation_instance
    with _delegation_lock:
        if _delegation_instance is None:
            _delegation_instance = DelegationManager(
                db_path=db_path,
                default_timeout_hours=default_timeout_hours,
            )
        return _delegation_instance


def reset_delegation_manager() -> None:
    """Reset the global DelegationManager (for testing)."""
    global _delegation_instance
    _delegation_instance = None


__all__ = [
    "_MAX_RETRIES",
    "_RETRY_DELAY",
    "DelegationManager",
    "DelegationRecord",
    "DelegationRule",
    "get_delegation_manager",
    "reset_delegation_manager",
]
