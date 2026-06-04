"""
ZENIC-AGENTS — Shared Knowledge Graph Engine.

Minimal in-memory knowledge graph for cross-agent knowledge sharing.
Provides a singleton get_knowledge_graph() for pub/sub node storage.
"""

from __future__ import annotations

import threading
from typing import Any


class _KnowledgeGraph:
    """Minimal in-memory knowledge graph."""

    def __init__(self) -> None:
        self._nodes: dict[str, Any] = {}
        self._edges: dict[str, Any] = {}
        self._lock = threading.Lock()

    def add_node(self, node: Any) -> str:
        """Store a knowledge node and return its ID."""
        with self._lock:
            self._nodes[node.id] = node
            return node.id

    def get_node(self, node_id: str) -> Any | None:
        """Retrieve a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def add_edge(self, edge: Any) -> str | None:
        """Store a knowledge edge and return its ID."""
        with self._lock:
            self._edges[edge.id] = edge
            return edge.id

    def get_neighbors(self, node_id: str, direction: str = "out") -> tuple[list[Any], list[Any]]:
        """Return (out_neighbors, in_neighbors) for a node."""
        out_nodes: list[Any] = []
        in_nodes: list[Any] = []
        for edge in self._edges.values():
            if direction in ("out", "both") and edge.source_id == node_id:
                target = self._nodes.get(edge.target_id)
                if target is not None:
                    out_nodes.append(target)
            if direction in ("in", "both") and edge.target_id == node_id:
                source = self._nodes.get(edge.source_id)
                if source is not None:
                    in_nodes.append(source)
        return out_nodes, in_nodes

    def query(self, query_obj: Any) -> Any:
        """Query nodes matching criteria (stub — returns empty result)."""
        # Return an object with a .nodes attribute (empty list)
        result = type("QueryResult", (), {"nodes": []})()
        return result

    def stats(self) -> dict[str, int]:
        """Return graph statistics."""
        with self._lock:
            return {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            }


# ── Singleton ──────────────────────────────────────────────────

_instance: _KnowledgeGraph | None = None
_instance_lock = threading.Lock()


def get_knowledge_graph() -> _KnowledgeGraph:
    """Return the singleton knowledge graph instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = _KnowledgeGraph()
    return _instance


def reset_knowledge_graph() -> None:
    """Reset the singleton (for tests)."""
    global _instance
    with _instance_lock:
        _instance = None
