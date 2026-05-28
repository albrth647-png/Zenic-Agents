"""
ZENIC-AGENTS - APA Planner v16 (Z3 Real + MCTS Real)

Planificador con MCTS real (UCB1, backpropagation, depth limiting)
y Solver real (Z3 con fallback AC-3, timeout enforcement).
"""

from ._imports import HAS_Z3, ExecutionPlan, OperationType, PlanStep, RoutePath
from .planner import APAPlanner

__all__ = [
    "HAS_Z3",
    "APAPlanner",
    "ExecutionPlan",
    "OperationType",
    "PlanStep",
    "RoutePath",
]
