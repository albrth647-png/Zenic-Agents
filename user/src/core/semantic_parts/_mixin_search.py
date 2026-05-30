"""
Mixin: Semantic search and clustering methods.
"""

from typing import Any

# Named constants (previously magic numbers)
_DEFAULT_SEARCH_TOP_K = 5
_DEFAULT_SEARCH_THRESHOLD = 0.5
_DEFAULT_SIMILAR_THRESHOLD = 0.7


class SearchMixin:
    """Semantic search and clustering for SemanticEngine."""

    def search(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = _DEFAULT_SEARCH_TOP_K,
        threshold: float = _DEFAULT_SEARCH_THRESHOLD,
    ) -> list[tuple[dict, float]]:
        """
        Búsqueda semántica en una lista de documentos.

        Args:
            query: Texto de búsqueda
            documents: Lista de dicts con "text" key
            top_k: Número máximo de resultados
            threshold: Similitud mínima para incluir

        Returns:
            Lista de (document, similarity) ordenada por similitud
        """
        if not self.is_loaded or not documents:
            return []

        query_emb = self.embed(query)
        if query_emb is None:
            return []

        results = []
        # Batch embed all documents for efficiency
        texts = [doc.get("text", "") for doc in documents]
        doc_embs = self.embed_batch(texts)

        for doc, doc_emb in zip(documents, doc_embs, strict=False):
            sim = self.similarity(query_emb, doc_emb)
            if sim >= threshold:
                results.append((doc, sim))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_similar_intents(
        self, text: str, history: list[str], threshold: float = _DEFAULT_SIMILAR_THRESHOLD
    ) -> list[tuple[str, float]]:
        """
        Encuentra consultas previas semánticamente similares.
        Útil para SmartMemory: detectar si ya respondimos algo similar.
        """
        if not self.is_loaded or not history:
            return []

        query_emb = self.embed(text)
        if query_emb is None:
            return []

        # Batch embed history
        hist_embs = self.embed_batch(history)
        results = []

        for hist_text, hist_emb in zip(history, hist_embs, strict=False):
            sim = self.similarity(query_emb, hist_emb)
            if sim >= threshold:
                results.append((hist_text, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results
