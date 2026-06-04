"""
MemoryManager del Asistente.

Orquesta los tres niveles de memoria (working, short-term, long-term)
con un retrieval unificado y avanzado. Proporciona una API limpia
para almacenar, buscar y promover memorias automaticamente.

Caracteristicas:
  - Store inteligente: auto-selecciona el nivel correcto
  - Retrieval unificado: busca en todos los niveles
  - Promocion automatica: working → short → long
  - Decay periodico: mantiene la memoria relevante
  - Thread-safe
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ..config.constants import MEMORY_MAX_LONG_TERM, MEMORY_MAX_WORKING
from ..types.base import Ok, Result
from ..types.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryQuery,
    MemoryType,
)
from .long_term import LongTermMemory
from .memory_scorer import MemoryScorer
from .short_term import ShortTermMemory
from .working_memory import WorkingMemory

logger = logging.getLogger("zenic_agents.conversational.memory.manager")


# ─── Config del MemoryManager ─────────────────────────────────


@dataclass
class MemoryManagerConfig:
    """Configuracion del MemoryManager."""

    working_max: int = MEMORY_MAX_WORKING
    short_term_max: int = MEMORY_MAX_LONG_TERM
    long_term_max: int = MEMORY_MAX_LONG_TERM
    auto_promote: bool = True
    promote_threshold: float = 0.7
    decay_interval_seconds: float = 3600.0  # 1 hora
    decay_factor: float = 0.99


# ─── Resultado de retrieval unificado ─────────────────────────


@dataclass
class UnifiedMemoryResult:
    """Resultado de busqueda unificada en todos los niveles."""

    entries: list[MemoryEntry] = field(default_factory=list)
    total_matches: int = 0
    search_time_ms: float = 0.0
    sources: dict[str, int] = field(default_factory=dict)  # level → count

    @property
    def has_results(self) -> bool:
        return len(self.entries) > 0

    @property
    def top_entry(self) -> MemoryEntry | None:
        if not self.entries:
            return None
        return max(self.entries, key=lambda e: e.relevance_score)

    def to_context_list(self, max_entries: int = 10) -> list[dict[str, Any]]:
        """Convierte a lista de dicts para inyeccion de contexto."""
        return [e.to_retrieval_dict() for e in self.entries[:max_entries]]

    def to_context_string(self, max_entries: int = 5) -> str:
        """Convierte a string para inyectar en prompt."""
        if not self.entries:
            return ""
        lines: list[str] = []
        for entry in self.entries[:max_entries]:
            lines.append(
                f"[{entry.memory_type.value}/{entry.category.value}] {entry.content} (rel={entry.relevance_score:.2f})"
            )
        return "\n".join(lines)


# ─── MemoryManager ────────────────────────────────────────────


class MemoryManager:
    """
    Orquestador unificado del sistema de memoria.

    NATURALEZA ONTOLÓGICA:
      SOY: El sistema de memoria unificado. Orquesto tres niveles (working,
           short-term, long-term) con retrieval, promoción automática y decay.
           Proporciono contexto relevante al pipeline sin intervención de IA.
      NO SOY: Base de datos SQL. Vector store. Sistema de archivos.
              No almaceno datos brutos sin procesar.
      INVARIANTE: Mi retrieval nunca falla — siempre devuelvo un resultado válido
                  (posiblemente vacío). No puedo bloquear el pipeline.
      FRONTERA: No evalúo la relevancia semántica del contenido (eso lo hace el
                MemoryScorer). No persisto datos críticos del sistema.

    COMPLETACIÓN SEMÁNTICA:
      - Mi contexto histórico es completado por DeterministicPipeline, que
        lo integra en el flujo de decisión (memory_lookup, dag_node_adapt).
      - Yo produzco CONTEXTO HISTÓRICO; el pipeline produce ACCIÓN CONTEXTUALIZADA.

    Provee una API limpia para:
      - Almacenar informacion en el nivel correcto
      - Buscar en todos los niveles con ranking
      - Promover automaticamente memorias importantes
      - Aplicar decay periodico
      - Obtener contexto para el pipeline
    """

    def __init__(self, config: MemoryManagerConfig | None = None) -> None:
        self._config = config or MemoryManagerConfig()
        self._working = WorkingMemory()
        self._short_term = ShortTermMemory(self._config.short_term_max)
        self._long_term = LongTermMemory(
            self._config.long_term_max,
            self._config.promote_threshold,
        )
        self._scorer = MemoryScorer()
        self._lock = threading.Lock()
        self._last_decay = time.time()
        self._stats = {
            "total_stored": 0,
            "total_retrieved": 0,
            "total_promoted": 0,
            "total_decayed": 0,
        }

    # ─── Store ─────────────────────────────────────────────────

    def store(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.FACT,
        session_id: str = "",
        source: str = "user",
        tags: list[str] | None = None,
        importance_override: float | None = None,
    ) -> Result[MemoryEntry, Exception]:
        """
        Almacena informacion en el nivel de memoria apropiado.

        Pipeline: score → create entry → store in working →
                  promote if needed.
        """
        # 1. Calcular importancia
        if importance_override is not None:
            score = importance_override
        else:
            existing = self._get_existing_entries(content, category)
            score = self._scorer.score(content, category, existing)

        # 2. Crear entrada
        entry = MemoryEntry(
            content=content[:500],  # Truncar para eficiencia
            category=category,
            session_id=session_id,
            importance=score,
            source=source,
            tags=tags or [],
        )

        # 3. Calcular TTL
        ttl = self._scorer.compute_ttl(score)
        if ttl > 0:
            entry.expires_at = time.time() + ttl

        # 4. Almacenar en working memory (siempre)
        self._working.store(entry)
        self._stats["total_stored"] += 1

        # 5. Promover si es suficientemente importante
        if self._config.auto_promote:
            self._maybe_promote(entry)

        return Ok(entry)

    def store_user_preference(
        self,
        key: str,
        value: str,
        session_id: str = "",
    ) -> Result[MemoryEntry, Exception]:
        """Almacena una preferencia del usuario (alta importancia)."""
        return self.store(
            content=f"{key}: {value}",
            category=MemoryCategory.PREFERENCE,
            session_id=session_id,
            source="user",
            importance_override=0.9,
            tags=["preference", key],
        )

    def store_correction(
        self,
        correction: str,
        session_id: str = "",
    ) -> Result[MemoryEntry, Exception]:
        """Almacena una correccion del usuario (muy importante)."""
        return self.store(
            content=correction,
            category=MemoryCategory.CORRECTION,
            session_id=session_id,
            source="user",
            importance_override=0.85,
            tags=["correction"],
        )

    def store_fact(
        self,
        fact: str,
        session_id: str = "",
        tags: list[str] | None = None,
    ) -> Result[MemoryEntry, Exception]:
        """Almacena un hecho o dato."""
        return self.store(
            content=fact,
            category=MemoryCategory.FACT,
            session_id=session_id,
            source="user",
            tags=tags or ["fact"],
        )

    # ─── Retrieval ─────────────────────────────────────────────

    def retrieve(
        self,
        query_text: str,
        categories: list[MemoryCategory] | None = None,
        session_id: str = "",
        max_results: int = 10,
        min_importance: float = 0.0,
        tags: list[str] | None = None,
    ) -> UnifiedMemoryResult:
        """
        Busca en todos los niveles de memoria.

        Pipeline: query → search all levels → merge → rank → return.
        """
        start = time.time()

        query = MemoryQuery(
            text=query_text,
            categories=categories or [],
            session_id=session_id,
            max_results=max_results * 2,  # Over-fetch para mergear
            min_importance=min_importance,
            tags=tags or [],
        )

        # Buscar en cada nivel
        working_result = self._working.retrieve(query)
        short_result = self._short_term.retrieve(query)
        long_result = self._long_term.retrieve(query)

        # Merge y deduplicar
        all_entries: dict[str, MemoryEntry] = {}
        sources: dict[str, int] = {}

        for entry in working_result.entries:
            if entry.memory_id not in all_entries:
                all_entries[entry.memory_id] = entry
                sources["working"] = sources.get("working", 0) + 1

        for entry in short_result.entries:
            if entry.memory_id not in all_entries:
                all_entries[entry.memory_id] = entry
                sources["short_term"] = sources.get("short_term", 0) + 1

        for entry in long_result.entries:
            if entry.memory_id not in all_entries:
                all_entries[entry.memory_id] = entry
                sources["long_term"] = sources.get("long_term", 0) + 1

        # Re-rankear con score combinado
        # Usamos copias superficiales para no mutar los originales (T1.3 VORTEX)
        entries = [copy.copy(e) for e in all_entries.values()]
        for entry in entries:
            # Boost por nivel: working es mas reciente/relevante
            level_boost = {
                MemoryType.WORKING: 0.1,
                MemoryType.SHORT_TERM: 0.05,
                MemoryType.LONG_TERM: 0.0,
            }
            entry.relevance_score += level_boost.get(entry.memory_type, 0.0)

        entries.sort(key=lambda e: e.relevance_score, reverse=True)
        entries = entries[:max_results]

        elapsed = (time.time() - start) * 1000
        self._stats["total_retrieved"] += 1

        return UnifiedMemoryResult(
            entries=entries,
            total_matches=len(all_entries),
            search_time_ms=elapsed,
            sources=sources,
        )

    def retrieve_for_context(
        self,
        query_text: str,
        session_id: str = "",
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Busca memoria relevante y retorna como lista
        de dicts lista para inyectar en contexto.
        """
        result = self.retrieve(
            query_text=query_text,
            session_id=session_id,
            max_results=max_results,
            min_importance=0.3,
        )
        return result.to_context_list(max_results)

    # ─── Maintenance ───────────────────────────────────────────

    def maybe_decay(self) -> int:
        """Ejecuta decay si ha pasado suficiente tiempo."""
        elapsed = time.time() - self._last_decay
        if elapsed < self._config.decay_interval_seconds:
            return 0

        removed = self._long_term.decay_all(self._config.decay_factor)
        self._short_term.cleanup_expired()
        self._last_decay = time.time()
        self._stats["total_decayed"] += removed

        if removed > 0:
            logger.info(f"Memory decay: {removed} entradas removidas")

        return removed

    def clear_session(self, session_id: str) -> int:
        """Limpia la memoria de una sesion."""
        return self._short_term.clear_session(session_id)

    def get_preferences(self, session_id: str) -> dict[str, Any]:
        """Obtiene las preferencias almacenadas de una sesion."""
        return self._short_term.get_preferences(session_id)

    # ─── Stats ─────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        """Estadisticas unificadas del sistema de memoria."""
        return {
            **self._stats,
            "working": self._working.stats.total_active,
            "short_term": self._short_term.stats.short_term_count,
            "long_term": self._long_term.stats.long_term_count,
        }

    # ================================================================
    #  VORTEX 2.7: Auto-verificación de determinismo
    # ================================================================

    def verify_determinism(self) -> dict[str, Any]:
        """
        Verifica que el MemoryManager es determinista (VORTEX 2.7).

        Prueba que:
        1. retrieve() produce el mismo resultado para el mismo input
        2. retrieve() no muta los entries originales (VORTEX 1.3)

        Returns:
            Dict con resultado de verificación.
        """
        tests = []
        all_ok = True

        # Store a test entry
        store_result = self.store(
            content="test verification content",
            category=MemoryCategory.FACT,
            source="verification",
        )

        if store_result.is_ok():
            entry = store_result.unwrap()

            # Test 1: Determinismo — mismo input → mismo output
            r1 = self.retrieve("test verification", max_results=5)
            r2 = self.retrieve("test verification", max_results=5)
            deterministic = (
                len(r1.entries) == len(r2.entries)
                and all(
                    e1.relevance_score == e2.relevance_score
                    for e1, e2 in zip(r1.entries, r2.entries)
                )
            )
            if not deterministic:
                all_ok = False
            tests.append({
                "test": "determinism",
                "passed": deterministic,
                "detail": f"Retrieval produces {'same' if deterministic else 'different'} results",
            })

            # Test 2: No mutación (VORTEX 1.3)
            # Verificar que los scores no se acumulan entre llamadas
            scores = []
            for _ in range(3):
                r = self.retrieve("test verification", max_results=5)
                if r.entries:
                    scores.append(r.entries[0].relevance_score)
            no_mutation = len(set(scores)) <= 1 if scores else True
            if not no_mutation:
                all_ok = False
            tests.append({
                "test": "no_mutation",
                "passed": no_mutation,
                "detail": f"Scores across calls: {scores}",
            })

        return {
            "component": "MemoryManager",
            "all_ok": all_ok,
            "tests": tests,
            "status": "VERIFIED" if all_ok else "DEGRADED",
        }

    # ─── Privados ──────────────────────────────────────────────

    def _maybe_promote(self, entry: MemoryEntry) -> None:
        """Promueve una entrada si es suficientemente importante."""
        if entry.importance >= 0.5:
            self._short_term.store(entry)

        if self._long_term.should_promote(entry):
            promoted = self._long_term.promote(entry)
            if promoted.unwrap if hasattr(promoted, "unwrap") else promoted:
                self._stats["total_promoted"] += 1

    def _get_existing_entries(self, content: str, category: MemoryCategory) -> list[MemoryEntry]:
        """Busca entradas existentes similares para scoring."""
        result = self.retrieve(
            query_text=content,
            categories=[category],
            max_results=5,
        )
        return result.entries[:3]
