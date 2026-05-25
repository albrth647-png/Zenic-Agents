"""
ZENIC-AGENTS — Level 4 APA Planner (Z3 Real + MCTS Real)

Adaptive Planning Architecture planner combining:

  - **Z3 SMT Solver** (surgical, 15s timeout) with AC-3 fallback
  - **MCTS** (Monte Carlo Tree Search) with UCB1 and depth limiting
  - **Abortive protocol** when solver exhausts budget
  - Three routing paths: SURGICAL, DEEP, FAST

Usage::

    from src.core.level4_apa_planner import APAPlanner, ExecutionPlan

    planner = APAPlanner()
    plan = planner.generate_plan(routing)
"""

from .planner_parts import APAPlanner, ExecutionPlan, PlanStep, OperationType, RoutePath, HAS_Z3

__all__ = [
    "APAPlanner",
    "ExecutionPlan",
    "PlanStep",
    "OperationType",
    "RoutePath",
    "HAS_Z3",
]
