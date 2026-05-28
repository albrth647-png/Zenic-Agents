"""
ZENIC-AGENTS - Symbolic Executor Sub-Package

Bounded Symbolic Execution engine with Z3 integration, path condition
management, statement-by-statement analysis, violation detection, and
concrete input generation.

This sub-package modularizes the original symbolic_executor.py into:
- types.py: SymbolicValue and SymbolicPath data types
- z3_bridge.py: Z3 variable management and constraint encoding mixin
- statement_processors.py: Simple statement processing mixin (assign, aug_assign, return, if)
- statement_loops.py: Loop and compound statement processing mixin (for, while, try, expr_stmt)
- executor_helpers.py: Value evaluation and symbolic expression helper mixin
- violations.py: Violation detection mixin
- concrete_gen.py: Concrete input generation mixin
- executor.py: Core SymbolicExecutor class composing all mixins

Public API (re-exported):
- SymbolicValue
- SymbolicPath
- SymbolicExecutor
"""

from ..z3_solver import HAS_Z3
from .executor import SymbolicExecutor
from .types import SymbolicPath, SymbolicValue

__all__ = ["HAS_Z3", "SymbolicExecutor", "SymbolicPath", "SymbolicValue"]
