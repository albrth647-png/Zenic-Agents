"""
semantic_parts — Modularized SemanticEngine components.
"""

from ._imports import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GOAL_PROTOTYPES,
    HAS_NUMPY,
    INTENT_PROTOTYPES,
    SemanticResult,
    _get_numpy,
)
from .engine import SemanticEngine

__all__ = [
    "EMBEDDING_DIM",
    "EMBEDDING_MODEL",
    "GOAL_PROTOTYPES",
    "HAS_NUMPY",
    "INTENT_PROTOTYPES",
    "SemanticEngine",
    "SemanticResult",
    "_get_numpy",
]
