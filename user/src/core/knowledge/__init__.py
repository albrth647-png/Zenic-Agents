from __future__ import annotations

try:
    from .types import GraphDomain, KnowledgeEdge, KnowledgeNode, KnowledgeQuery, KnowledgeSearchResult
except ImportError:
    KnowledgeNode = None  # type: ignore[misc,assignment]
    KnowledgeEdge = None  # type: ignore[misc,assignment]
    KnowledgeQuery = None  # type: ignore[misc,assignment]
    KnowledgeSearchResult = None  # type: ignore[misc,assignment]
    GraphDomain = None  # type: ignore[misc,assignment]

try:
    from .graph_engine import KnowledgeGraphEngine, get_knowledge_graph, reset_knowledge_graph
except ImportError:
    KnowledgeGraphEngine = None  # type: ignore[misc,assignment]
    get_knowledge_graph = None  # type: ignore[misc,assignment]
    reset_knowledge_graph = None  # type: ignore[misc,assignment]

# CrossAgentKnowledgeBus archived — unused (zero external references).
# Files preserved in _archived/agents/shared/cross_agent.py

__all__ = [
    "GraphDomain",
    "KnowledgeEdge",
    "KnowledgeGraphEngine",
    "KnowledgeNode",
    "KnowledgeQuery",
    "KnowledgeSearchResult",
    "get_knowledge_graph",
    "reset_knowledge_graph",
]
