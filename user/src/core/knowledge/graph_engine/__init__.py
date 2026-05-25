"""Re-exports for graph_engine package."""

import threading
from typing import Optional

from ._mixin_core import KnowledgeGraphEngine

_instance: KnowledgeGraphEngine | None = None
_instance_lock = threading.Lock()


def get_knowledge_graph() -> KnowledgeGraphEngine:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = KnowledgeGraphEngine()
    return _instance


def reset_knowledge_graph() -> None:
    global _instance
    with _instance_lock:
        _instance = None


__all__ = [
    "KnowledgeGraphEngine",
    "get_knowledge_graph",
    "reset_knowledge_graph",
]
