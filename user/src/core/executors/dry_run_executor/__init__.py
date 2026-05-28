"""
ZENIC-AGENTS - Dry-Run Executor (C1: Simulation Engine)

Wraps real executors and intercepts I/O to simulate execution without
real side-effects.  Every operation is recorded but nothing is actually
performed: SMTP sends are blocked, HTTP calls are skipped, DB writes
use journal snapshots instead of real mutations, and file writes are
suppressed.

Thread-safe: All public methods guarded by RLock.
Retry logic: Critical operations wrapped with 3 retries, exponential
backoff (0.1s, 0.2s, 0.4s).
Singleton: get_dry_run_executor() / reset_dry_run_executor().
"""

from ._dispatch import dry_run_dispatch, get_dry_run_executor, reset_dry_run_executor
from ._mixin_core import DryRunExecutor
from ._types import DryRunOperation, DryRunResult

__all__ = [
    "DryRunExecutor",
    "DryRunOperation",
    "DryRunResult",
    "dry_run_dispatch",
    "get_dry_run_executor",
    "reset_dry_run_executor",
]
