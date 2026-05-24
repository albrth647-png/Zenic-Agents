"""Re-exports for graph_engine package."""

import threading
from typing import Optional

_instance: KnowledgeGraphEngine | None = None  # noqa: F821  # TODO: verify import
_instance_lock = threading.Lock()


def get_knowledge_graph() -> KnowledgeGraphEngine:  # noqa: F821  # TODO: verify import
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = KnowledgeGraphEngine()  # noqa: F821  # TODO: Phase3 - verify import
    return _instance


def reset_knowledge_graph() -> None:
    global _instance
    with _instance_lock:
        _instance = None
