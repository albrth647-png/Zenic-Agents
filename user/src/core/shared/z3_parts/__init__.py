"""
Z3 Solver Sub-Package.

Modular decomposition of the Z3 SMT Solver wrapper.

Re-exports all public symbols for backward compatibility.
"""

from .ac3_fallback import AC3FallbackMixin
from .invariants import Z3InvariantMixin
from .invariants_patterns import Z3InvariantPatternsMixin
from .null_safety import Z3NullSafetyMixin
from .solver import HAS_Z3, Z3Solver
from .solver_core import Z3SolverCoreMixin
from .solver_encoding import Z3SolverEncodingMixin
from .type_lattice import Z3TypeLatticeMixin
from .type_safety import Z3TypeSafetyMixin
from .z3_context import z3_session

__all__ = [
    "HAS_Z3",
    "AC3FallbackMixin",
    "Z3InvariantMixin",
    "Z3InvariantPatternsMixin",
    "Z3NullSafetyMixin",
    "Z3Solver",
    "Z3SolverCoreMixin",
    "Z3SolverEncodingMixin",
    "Z3TypeLatticeMixin",
    "Z3TypeSafetyMixin",
    "z3_session",
]
