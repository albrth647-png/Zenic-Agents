"""
A40 DeterministicPipeline — Execute all 7 deterministic tasks without AI.

DEPRECATED: This agent violates the SRP invariant (7 tasks in 1 agent).
Individual A01-A04 agents should be used instead.
"""

from ._constants import (
    EXT_LANG_MAP,
    GAP_DEFAULTS,
    GOAL_KEYWORDS,
    OP_KEYWORDS,
    PATTERN_HEURISTICS,
    PATTERN_LIBRARY,
    VIOLATION_CATALOG,
)
from ._core import DeterministicPipeline

__all__ = [
    "EXT_LANG_MAP",
    "GAP_DEFAULTS",
    "GOAL_KEYWORDS",
    "OP_KEYWORDS",
    "PATTERN_HEURISTICS",
    "PATTERN_LIBRARY",
    "VIOLATION_CATALOG",
    "DeterministicPipeline",
]
