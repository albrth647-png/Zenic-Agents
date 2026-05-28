"""
Zenic-Agents ROI — Cost Accumulator

Tracks cost per action across LLM tokens, API calls, compute time,
human time, storage, and network usage. Persists entries in SQLite
with thread-safe access, retry logic, and graceful degradation.
"""

import threading
from typing import Any, Optional

from ._mixin_core import CostAccumulator
from ._types import DEFAULT_UNIT_COSTS, CostCategory, CostEntry

__all__ = [
    "DEFAULT_UNIT_COSTS",
    "CostAccumulator",
    "CostCategory",
    "CostEntry",
    "get_cost_accumulator",
    "reset_cost_accumulator",
]


# ── Singleton ────────────────────────────────────────────

_cost_accumulator: CostAccumulator | None = None
_lock = threading.Lock()


def get_cost_accumulator(**kwargs: Any) -> CostAccumulator:
    """Get or create the global CostAccumulator singleton."""
    global _cost_accumulator
    with _lock:
        if _cost_accumulator is None:
            _cost_accumulator = CostAccumulator(**kwargs)
        return _cost_accumulator


def reset_cost_accumulator() -> None:
    """Reset the global CostAccumulator (for testing)."""
    global _cost_accumulator
    _cost_accumulator = None
