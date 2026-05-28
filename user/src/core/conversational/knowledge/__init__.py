"""
Base de conocimiento del Asistente.

Almacena y recupera conocimiento estructurado para
enriquecer las respuestas del asistente.
"""

from ._base import KnowledgeBase
from ._types import (
    KnowledgeEntry,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeType,
)

__all__ = [
    "KnowledgeBase",
    "KnowledgeEntry",
    "KnowledgeQuery",
    "KnowledgeResult",
    "KnowledgeType",
]
