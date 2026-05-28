"""Shared imports for planner_parts.

FIX (Phase 4): Removed unused import (ConstraintSolver) that is never
consumed by child modules via `from ._imports import`. Only the names
actually used by planner_parts modules are imported.
"""

import gc
import logging
import time
import uuid

from src.config.loader import (
    get_k_path_limit,
    get_mcts_config,
    get_solver_fast_timeout_ms,
    get_solver_timeout_ms,
    load_settings,
)
from src.core.shared.contracts import (
    HAS_Z3,
    CodeConstraintBuilder,
    Constraint,
    ExecutionPlan,
    MCTSPlanner,
    OperationType,
    PlanStep,
    RoutePath,
    TimeoutEnforcer,
    Z3Solver,
)
from src.core.shared.resource_governor import get_governor

logger = logging.getLogger(__name__)

__all__ = [
    "HAS_Z3",
    "CodeConstraintBuilder",
    "Constraint",
    "ExecutionPlan",
    "MCTSPlanner",
    "OperationType",
    "PlanStep",
    "RoutePath",
    "TimeoutEnforcer",
    "Z3Solver",
    "gc",
    "get_governor",
    "get_k_path_limit",
    "get_mcts_config",
    "get_solver_fast_timeout_ms",
    "get_solver_timeout_ms",
    "load_settings",
    "logger",
    "time",
    "uuid",
]
