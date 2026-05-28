"""
ZENIC-AGENTS - Contratos de Datos v16 (Facade Module)

This module re-exports all contracts from their dedicated sub-modules
for backward compatibility. The original monolith has been decomposed into:

- types.py: Data types and payloads
- mcts.py: Monte Carlo Tree Search
- constraint_solver.py: AC-3 + Backtracking CSP solver
- z3_solver.py: Z3 SMT Solver wrapper
- timeout.py: Timeout enforcement
- code_constraints.py: Code constraint builder
- symbolic_executor.py: Symbolic execution engine
- kpath_analyzer.py: K-Path dependency analyzer

Any code that does `from src.core.shared.contracts import X` will continue to work.
"""

from .constraint_solver import Constraint, ConstraintSolver
from .mcts import MCTSNode, MCTSPlanner
from .timeout import TimeoutEnforcer
from .types import (
    CRITICALITY_INT_TO_PATH,
    CRITICALITY_INT_TO_STR,
    CRITICALITY_PATH_TO_INT,
    CRITICALITY_STR_TO_INT,
    ChatMessage,
    ChatRequest,
    CriticalityLevel,
    ExecutionPlan,
    GoalType,
    IntentPayload,
    MerkleNode,
    OperationType,
    PlanStep,
    RoutePath,
    RoutingPayload,
    SandboxResult,
    criticality_to_int,
    criticality_to_path,
    criticality_to_str,
)
from .z3_solver import HAS_Z3, Z3Solver

try:
    from .code_constraints import CodeConstraintBuilder  # type: ignore[import-unresolved]
except ImportError:
    CodeConstraintBuilder = None  # type: ignore[misc,assignment]
from .kpath_analyzer import KPathAnalyzer
from .symbolic_executor import SymbolicExecutor, SymbolicPath, SymbolicValue

__all__ = [
    "CRITICALITY_INT_TO_PATH",
    "CRITICALITY_INT_TO_STR",
    "CRITICALITY_PATH_TO_INT",
    "CRITICALITY_STR_TO_INT",
    "HAS_Z3",
    "ChatMessage",
    "ChatRequest",
    "CodeConstraintBuilder",
    "Constraint",
    "ConstraintSolver",
    "CriticalityLevel",
    "ExecutionPlan",
    "GoalType",
    "IntentPayload",
    "KPathAnalyzer",
    "MCTSNode",
    "MCTSPlanner",
    "MerkleNode",
    "OperationType",
    "PlanStep",
    "RoutePath",
    "RoutingPayload",
    "SandboxResult",
    "SymbolicExecutor",
    "SymbolicPath",
    "SymbolicValue",
    "TimeoutEnforcer",
    "Z3Solver",
    "criticality_to_int",
    "criticality_to_path",
    "criticality_to_str",
]
