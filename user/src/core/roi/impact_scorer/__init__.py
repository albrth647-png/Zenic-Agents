"""
Zenic-Agents ROI — Impact Scorer

Economic impact scoring per alert, event, and action. Estimates
potential loss if no action is taken and potential gain if action
is taken, weighted by urgency.  Persists in SQLite with
thread-safe access, retry logic, and graceful degradation.
"""

import threading
from typing import Any, Optional

from ._mixin_core import ImpactScorer
from ._types import ImpactScore

__all__ = [
    "ImpactScore",
    "ImpactScorer",
    "get_impact_scorer",
    "reset_impact_scorer",
]


# ── Singleton ────────────────────────────────────────────

_impact_scorer: ImpactScorer | None = None
_lock = threading.Lock()


def get_impact_scorer(**kwargs: Any) -> ImpactScorer:
    """Get or create the global ImpactScorer singleton."""
    global _impact_scorer
    with _lock:
        if _impact_scorer is None:
            _impact_scorer = ImpactScorer(**kwargs)
        return _impact_scorer


def reset_impact_scorer() -> None:
    """Reset the global ImpactScorer (for testing)."""
    global _impact_scorer
    _impact_scorer = None
