"""
ZENIC-AGENTS v16 - Vector Store Module (Phase 4.1)

Provides pgvector-backed vector storage for semantic search,
replacing the O(n) linear scan in SemanticEngine with O(log n)
nearest neighbor search via HNSW indexes.

Components:
- VectorStore: Async pgvector client for storing/querying embeddings
- HNSWIndex: In-memory HNSW index for ultra-fast ANN search
- VectorHealthCheck: Integration with the HealthAggregator
"""

from .hnsw_index import HNSWIndex
from .vector_store import VectorStore, get_vector_store

__all__ = [
    "HNSWIndex",
    "VectorStore",
    "get_vector_store",
]
