"""
ZENIC-AGENTS - Objective Data Model & Persistence (Phase D1)

Objective data model and SQLite persistence for the Autopilot by Objectives
system. Objectives represent business goals like "reduce overdue invoices to <5%"
with measurable targets, priorities, and lifecycle management.

Thread-safe: All public methods guarded by RLock.
Retry logic: DB operations wrapped with 3 retries, base 0.5s backoff.
"""

from ._manager import (
    ObjectiveStore,
    get_objective_store,
    reset_objective_store,
)
from ._scoring import (
    Objective,
    ObjectivePriority,
    ObjectiveStatus,
    ObjectiveTarget,
)

__all__ = [
    "Objective",
    "ObjectivePriority",
    "ObjectiveStatus",
    "ObjectiveStore",
    "ObjectiveTarget",
    "get_objective_store",
    "reset_objective_store",
]
