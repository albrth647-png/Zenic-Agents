"""
ZENIC-AGENTS - SemanticEngine (Facade)

Thin facade — all logic lives in semantic_parts/.
"""

from .semantic_parts import SemanticEngine, SemanticResult

__all__ = [
    "SemanticEngine",
    "SemanticResult",
]
