"""
Zenic-Agents Asistente - Risk-Based Approval Routing (Phase C3)

Routes approval requests based on a contextual risk score computed from
multiple factors: action category, monetary amount, target environment,
time of day, and user history.
"""

# ── Singleton ─────────────────────────────────────────────
import threading
from typing import Optional

from ._mixin_core import RiskBasedApprovalRouter
from ._types import (
    _ACTION_CATEGORY_SCORES,
    _MAX_RETRIES,
    _RETRY_DELAY,
    _ROLE_LEVELS,
    RiskAssessment,
    RiskLevel,
    _score_to_risk_level,
    _score_to_role,
)

_risk_router_instance: RiskBasedApprovalRouter | None = None
_risk_router_lock = threading.Lock()


def get_risk_router(db_path: str = "risk_routing.sqlite") -> RiskBasedApprovalRouter:
    """Get or create the global RiskBasedApprovalRouter instance."""
    global _risk_router_instance
    with _risk_router_lock:
        if _risk_router_instance is None:
            _risk_router_instance = RiskBasedApprovalRouter(db_path=db_path)
        return _risk_router_instance


def reset_risk_router() -> None:
    """Reset the global RiskBasedApprovalRouter (for testing)."""
    global _risk_router_instance
    _risk_router_instance = None


__all__ = [
    "_ACTION_CATEGORY_SCORES",
    "_MAX_RETRIES",
    "_RETRY_DELAY",
    "_ROLE_LEVELS",
    "RiskAssessment",
    "RiskBasedApprovalRouter",
    "RiskLevel",
    "_score_to_risk_level",
    "_score_to_role",
    "get_risk_router",
    "reset_risk_router",
]
