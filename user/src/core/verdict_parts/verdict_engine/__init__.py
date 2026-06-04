"""
VerdictEngine — Motor de Veredicto.

NATURALEZA ONTOLÓGICA:
  SOY: El árbitro final del sistema. Recibo una pregunta binaria y evidencia
       estructurada, y emito un veredicto SÍ/NO como árbitro de último recurso.
  NO SOY: Generador de contenido, clasificador, chatbot. Nunca decido sin
          evidencia.
  INVARIANTE: Toda decisión tiene un rastro de evidencia. Nunca emito un
              veredicto sin al menos un intento de consenso determinístico.
  FRONTERA: No ejecuto código. No clasifico intenciones. No extraigo
            entidades. No genero texto. Solo arbitro entre opciones binarias.

COMPLETACIÓN SEMÁNTICA:
  - ConsensusResolver produce INDETERMINACIÓN ("no sé")
  - Yo produzco RESOLUCIÓN FINAL (SÍ/NO)

  - Mi veredicto es completado por ZenicOrchestrator, que toma el SÍ/NO
    y lo convierte en ACCIÓN (commit, rollback, NO_OP).
"""

import concurrent.futures
import logging
import os
import re
import threading
import time
from typing import Any, List

from ..consensus_resolver import ConsensusResolver
from ..deterministic_pipeline import DeterministicPipeline
from ..evidence_collector import EvidenceCollector
from ..types import (
    ConsensusResult,
    Evidence,
    EvidenceType,
    Verdict,
    VerdictConfidence,
    VerdictInput,
    VerdictOutput,
)

try:
    from ..resilience import (
        VerdictAuditEntry,
        VerdictAuditor,
        VerdictCircuitBreaker,
        VerdictHealthMonitor,
        VerdictResilienceOrchestrator,
        VerdictRetryConfig,
    )

    _RESILIENCE_AVAILABLE = True
except ImportError:
    _RESILIENCE_AVAILABLE = False

import contextlib

from ._config import (
    VERDICT_CONSENSUS_ATTEMPTS,
    VERDICT_CONSENSUS_THRESHOLD,
    VERDICT_MAX_RETRIES,
    VERDICT_MAX_TOKENS,
    VERDICT_TEMPERATURE,
    VERDICT_TIMEOUT_S,
)
from ._helpers_mixin import VerdictHelpersMixin
from ._llm_mixin import VerdictLLMMixin
from ..geodesic import GeodesicPath, GeodesicTracker, VerdictState

logger = logging.getLogger("zenic_agents.verdict_parts.verdict_engine")

__all__ = [
    "VERDICT_CONSENSUS_THRESHOLD",
    "VERDICT_MAX_TOKENS",
    "VERDICT_TEMPERATURE",
    "ConsensusResult",
    "VerdictAuditEntry",
    "VerdictEngine",
    "os",
    "re",
]

class VerdictEngine(VerdictLLMMixin, VerdictHelpersMixin):
    """Motor de Veredicto: la IA solo dice SI o NO."""

    def __init__(self, mini_ai=None, semantic_engine=None, smart_memory=None, auto_load: bool = True):
        """
        Args:
            mini_ai: Instancia de MiniAIEngine (Qwen3-0.6B) - OPCIONAL
            semantic_engine: Instancia de SemanticEngine - OPCIONAL
            smart_memory: Instancia de SmartMemory - OPCIONAL
            auto_load: Si True, carga el modelo al inicializar
        """
        self._mini_ai = mini_ai
        self._semantic = semantic_engine
        self._memory = smart_memory
        self._memory_chip = None  # Injected from _zenic_native

        # Subsistemas determinísticos (siempre disponibles)
        self._pipeline = DeterministicPipeline()
        self._evidence_collector = EvidenceCollector()
        self._consensus_resolver = ConsensusResolver()

        # Stats (thread-safe)
        self._stats_lock = threading.Lock()
        self._total_verdicts = 0
        self._llm_verdicts = 0
        self._consensus_verdicts = 0
        self._low_confidence_verdicts = 0
        self._fallback_verdicts = 0
        self._yes_count = 0
        self._no_count = 0
        self._total_time = 0.0

        # Executor para timeout
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        # v17.1: Resilience orchestrator
        if _RESILIENCE_AVAILABLE:
            self._resilience = VerdictResilienceOrchestrator(
                circuit_breaker=VerdictCircuitBreaker(
                    name="verdict_engine",
                    failure_threshold=3,
                    recovery_timeout=60.0,
                    half_open_max_calls=2,
                    success_threshold=2,
                ),
                health_monitor=VerdictHealthMonitor(
                    window_size=50,
                    unhealthy_threshold=0.3,
                ),
                auditor=VerdictAuditor(max_entries=200),
                retry_config=VerdictRetryConfig(
                    max_attempts=VERDICT_MAX_RETRIES,
                    base_delay=1.0,
                    max_delay=10.0,
                    timeout_per_attempt=VERDICT_TIMEOUT_S,
                ),
            )
        else:
            self._resilience = None

        # VORTEX 2.4: TopologicalRouter (inyectable externamente)
        self._topology_router = None
        # VORTEX 2.5: GeodesicTracker (inyectable externamente)
        self._geodesic_tracker = None

    def set_memory_chip(self, chip) -> None:
        """Inject the Memory Chip reference (via PyO3 bridge)."""
        self._memory_chip = chip

    def shutdown(self):
        """Shut down the internal ThreadPoolExecutor to prevent resource leaks.

        Call this when the VerdictEngine is no longer needed (e.g. on server
        shutdown).  Without this the executor's worker thread keeps running.
        """
        executor = getattr(self, "_executor", None)
        if executor is not None:
            executor.shutdown(wait=False)
            self._executor = None

    def __del__(self):
        """Ensure executor is cleaned up on garbage collection."""
        with contextlib.suppress(Exception):
            self.shutdown()

        # NOTE: Do NOT log here — __del__ runs during garbage collection and
        # referencing self._mini_ai / self._semantic may already be invalid.
        # The original code used bare names (mini_ai, semantic_engine) which
        # caused NameError at GC time.

    # ================================================================
    #  MAIN API: Full verdict pipeline
    # ================================================================

    def verdict(
        self,
        text: str,
        code: str = "",
        language: str = "python",
        question: str = "Should this code be approved?",
        context: dict[str, Any] | None = None,
    ) -> VerdictOutput:
        """
        Ejecuta el pipeline completo de veredicto con resiliencia.

        Este es el punto de entrada principal. Recorre:
          1. DeterministicPipeline (tareas sin IA)
          2. EvidenceCollector (evidencia sin IA)
          3. ConsensusResolver (consenso sin IA)
          4. Si hay empate → Circuit Breaker check → LLM arbitraje
          5. Multi-attempt consensus para mayor confiabilidad
          6. Audit del resultado

        VORTEX 2.5: La ejecución sigue una geodésica documentada.
        VORTEX 2.4: Los fallos se redistribuyen topológicamente.
        """
        _tracker = getattr(self, "_geodesic_tracker", None)
        if _tracker is not None:
            _tracker.start({"question": question[:100]})

        start_time = time.time()
        with self._stats_lock:
            self._total_verdicts += 1
        ctx = context or {}

        # === MEMORY CHIP PRE-CHECK (T2-17, T1-15) ===
        # If the memory chip has a high-confidence mapping, bypass the entire
        # verdict pipeline and return immediately. This is the <5ms path.
        if self._memory_chip is None:
            logger.debug("Memory chip not initialized — PyO3 module may not be loaded")
        if self._memory_chip is not None:
            try:
                chip_result = self._memory_chip.lookup(text, ctx.get("tenant_id", "__anonymous__"))
                if chip_result and chip_result.get("cache_hit"):
                    # SECURITY (C1 fix): Before returning YES from cache,
                    # run ONLY security/sandbox evidence checks (not ALL collectors)
                    # to keep the fast path <5ms.
                    veto_evidence = self._evidence_collector.collect_code_safety_evidence(code)
                    has_veto = any(
                        e.favors == Verdict.NO
                        and e.evidence_type in (EvidenceType.SECURITY_CHECK, EvidenceType.SANDBOX_PASS)
                        and e.weight >= 0.7
                        for e in veto_evidence
                    )
                    if has_veto:
                        logger.warning(
                            "Memory chip cache hit for '%s' overridden by veto evidence — "
                            "falling through to full pipeline",
                            text[:80],
                        )
                        # Fall through to normal pipeline below
                    else:
                        mapping = chip_result.get("mapping", {})
                        confidence = 0.9  # Memory chip mappings are pre-approved
                        with self._stats_lock:
                            self._consensus_verdicts += 1
                            self._yes_count += 1
                        elapsed_cache = time.time() - start_time
                        self._audit_result(
                            text[:200],
                            "YES",
                            "memory_chip_cache",
                            False,
                            confidence,
                            int(elapsed_cache * 1000),
                            0,
                            0,
                            0,
                            0.0,
                        )
                        # VORTEX 2.5: Geodésica CACHE (0 → 4)
                        if _tracker is not None:
                            _tracker.visit(VerdictState.PIPELINE_COMPLETED)
                            _tracker.visit(VerdictState.EVIDENCE_COLLECTED)
                            _tracker.visit(VerdictState.CONSENSUS_RESOLVED)
                            _tracker.visit(VerdictState.VERDICT_CACHE_HIT)
                            _tracker.resolve_geodesic(GeodesicPath.CACHE)
                            _tracker.complete()
                        return VerdictOutput(
                            verdict=Verdict.YES,
                            confidence=confidence,
                            source="memory_chip_cache",
                            evidence_summary=f"Memory chip cache hit: '{text}' → '{mapping.get('destination', '?')}' "
                            f"(mechanism: {mapping.get('mechanism', 'unknown')})",
                            llm_used=False,
                            llm_raw_response="",
                            retry_count=0,
                        )
            except Exception as exc:
                logger.debug("Memory chip pre-check error: %s", exc)

        # === PASO 1: Ejecutar pipeline determinístico ===
        pipeline_results = self._pipeline.execute_all(text, code, language, ctx)
        if _tracker is not None:
            _tracker.visit(VerdictState.PIPELINE_COMPLETED)

        # === PASO 2: Recolectar evidencia ===
        evidence = self._evidence_collector.collect_all_evidence(
            text,
            code,
            language,
            memory_chip=self._memory_chip,
            tenant_id=ctx.get("tenant_id", "__anonymous__"),
        )
        if _tracker is not None:
            _tracker.visit(VerdictState.EVIDENCE_COLLECTED)

        # Agregar evidencia de los resultados del pipeline
        for task_name, result in pipeline_results.items():
            if result.confidence >= 0.8:
                evidence.append(
                    Evidence(
                        evidence_type=EvidenceType.RULE_ENGINE,
                        favors=Verdict.YES,
                        weight=result.confidence,
                        source=f"pipeline_{task_name}",
                        detail=f"Pipeline task {task_name} succeeded with confidence {result.confidence:.2f}",
                    )
                )

        # === PASO 3: Resolver consenso ===
        consensus = self._consensus_resolver.resolve(evidence, question)
        if _tracker is not None:
            _tracker.visit(VerdictState.CONSENSUS_RESOLVED)

        # Check for veto (security veto is always DENY)
        has_veto = any(
            e.favors == Verdict.NO
            and e.evidence_type in (EvidenceType.SECURITY_CHECK, EvidenceType.SANDBOX_PASS)
            and e.weight >= 0.9
            for e in evidence
        )

        # === PASO 4: Decidir si necesita IA ===
        if not consensus.needs_llm:
            # Consenso claro: no necesita IA
            elapsed = time.time() - start_time
            with self._stats_lock:
                self._total_time += elapsed

                if consensus.confidence in (VerdictConfidence.CERTAIN, VerdictConfidence.HIGH):
                    self._consensus_verdicts += 1
                else:
                    self._low_confidence_verdicts += 1

                if consensus.verdict == Verdict.YES:
                    self._yes_count += 1
                else:
                    self._no_count += 1

            evidence_summary = self._build_evidence_summary(consensus)

            self._audit_result(
                question,
                consensus.verdict.value,
                "consensus",
                False,
                abs(consensus.score),
                int(elapsed * 1000),
                0,
                len(consensus.evidence_for),
                len(consensus.evidence_against),
                consensus.score,
            )

            # VORTEX 2.5: Geodésica CONSENSUS (0 → 1 → 2 → 3 → 5) o VETO (0 → 1 → 2 → 8)
            if _tracker is not None:
                if has_veto:
                    _tracker.visit(VerdictState.VERDICT_VETO)
                    _tracker.resolve_geodesic(GeodesicPath.VETO)
                else:
                    _tracker.visit(VerdictState.VERDICT_CONSENSUS)
                    _tracker.resolve_geodesic(GeodesicPath.CONSENSUS)
                _tracker.complete()

            return VerdictOutput(
                verdict=consensus.verdict,
                confidence=abs(consensus.score),
                source="consensus",
                evidence_summary=evidence_summary,
                llm_used=False,
                llm_raw_response="",
                retry_count=0,
            )

        # === PASO 5: Arbitraje de IA con resiliencia ===
        if self._resilience is None:
            logger.debug("Resilience orchestrator not available — running without circuit breaker")
        verdict_input = VerdictInput(
            question=question,
            evidence_for=consensus.evidence_for,
            evidence_against=consensus.evidence_against,
            consensus_score=consensus.score,
            context=self._build_context_summary(text, code, pipeline_results),
        )

        # VORTEX 2.5: Geodésica LLM (0 → 1 → 2 → 3 → 6) o FALLBACK (0 → 1 → 2 → 3 → 7)
        # Se resolverá según el resultado de _request_llm_verdict
        if _tracker is not None:
            _tracker.resolve_geodesic(GeodesicPath.LLM)
            _tracker.visit(VerdictState.VERDICT_LLM)
            _tracker.complete()

        return self._request_llm_verdict(verdict_input, start_time)

    # ================================================================
    #  DIRECT API: Ask LLM directly (only YES/NO)
    # ================================================================

    def ask_yes_no(
        self,
        question: str,
        context: str = "",
        evidence_for: list[Evidence] | None = None,
        evidence_against: list[Evidence] | None = None,
    ) -> VerdictOutput:
        """
        Pregunta directamente a la IA una pregunta de SÍ o NO.

        v17.1: Ahora con circuit breaker, retry, y consensus.
        """
        start_time = time.time()
        with self._stats_lock:
            self._total_verdicts += 1

        verdict_input = VerdictInput(
            question=question,
            evidence_for=evidence_for or [],
            evidence_against=evidence_against or [],
            consensus_score=0.0,
            context=context,
        )

        return self._request_llm_verdict(verdict_input, start_time)

    # ================================================================
    #  STATS
    # ================================================================

    @property
    def stats(self) -> dict[str, Any]:
        """Estadísticas del VerdictEngine con resiliencia."""
        with self._stats_lock:
            total_verdicts = self._total_verdicts
            llm_verdicts = self._llm_verdicts
            consensus_verdicts = self._consensus_verdicts
            low_confidence_verdicts = self._low_confidence_verdicts
            fallback_verdicts = self._fallback_verdicts
            yes_count = self._yes_count
            no_count = self._no_count
            total_time = self._total_time
        total = max(total_verdicts, 1)
        base_stats = {
            "total_verdicts": total_verdicts,
            "llm_verdicts": llm_verdicts,
            "consensus_verdicts": consensus_verdicts,
            "low_confidence_verdicts": low_confidence_verdicts,
            "fallback_verdicts": fallback_verdicts,
            "yes_count": yes_count,
            "no_count": no_count,
            "llm_rate": llm_verdicts / total,
            "consensus_rate": consensus_verdicts / total,
            "low_confidence_rate": low_confidence_verdicts / total,
            "fallback_rate": fallback_verdicts / total,
            "yes_rate": yes_count / total,
            "no_rate": no_count / total,
            "avg_time_s": total_time / total,
            "llm_available": self._mini_ai is not None and self._mini_ai.is_loaded,
            "consensus_attempts": VERDICT_CONSENSUS_ATTEMPTS,
            "max_retries": VERDICT_MAX_RETRIES,
        }
        if self._resilience:
            base_stats["resilience"] = self._resilience.stats
        return base_stats

    @property
    def health(self) -> dict[str, Any]:
        """Health status of the verdict system."""
        if self._resilience:
            snap = self._resilience.health_snapshot
            return {
                "is_healthy": snap.is_healthy,
                "success_rate": snap.success_rate,
                "avg_latency_s": snap.avg_latency_s,
                "circuit_breaker_state": snap.circuit_breaker_state,
            }
        return {
            "is_healthy": self._mini_ai is not None and self._mini_ai.is_loaded,
            "success_rate": "unknown",
            "avg_latency_s": "unknown",
            "circuit_breaker_state": "not_configured",
        }

    # ================================================================
    #  LIFECYCLE
    # ================================================================

    def update_engines(self, mini_ai=None, semantic_engine=None, smart_memory=None, memory_chip=None) -> None:
        """Actualiza las referencias a los motores."""
        if mini_ai is not None:
            self._mini_ai = mini_ai
        if semantic_engine is not None:
            self._semantic = semantic_engine
        if smart_memory is not None:
            self._memory = smart_memory
        if memory_chip is not None:
            self._memory_chip = memory_chip
            # Also inject into the pipeline
            self._pipeline.set_memory_chip(memory_chip)

        logger.info(
            f"VerdictEngine: Updated engines - "
            f"LLM={'available' if self._mini_ai and self._mini_ai.is_loaded else 'not available'}"
        )

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to CLOSED state."""
        if self._resilience:
            self._resilience.circuit_breaker.reset()
            logger.info("VerdictEngine: Circuit breaker reset to CLOSED")

    def get_audit_trail(self, count: int = 20) -> list[dict[str, Any]]:
        """Get recent audit entries as dictionaries."""
        if self._resilience and _RESILIENCE_AVAILABLE:
            entries = self._resilience.auditor.get_recent(count)
            return [
                {
                    "timestamp": e.timestamp,
                    "question": e.question,
                    "verdict": e.verdict,
                    "source": e.source,
                    "llm_used": e.llm_used,
                    "confidence": e.confidence,
                    "latency_ms": e.latency_ms,
                    "circuit_breaker_state": e.circuit_breaker_state,
                }
                for e in entries
            ]
        return []

    def get_failure_pattern(self) -> dict[str, Any]:
        """Analyze recent verdicts for failure patterns."""
        if self._resilience:
            return self._resilience.auditor.get_failure_pattern()
        return {"pattern": "no_data", "risk": "unknown"}

    # ================================================================
    #  VORTEX 2.7: Auto-verificación de determinismo
    # ================================================================

    def verify_determinism(self) -> dict[str, Any]:
        """
        Verifica que el VerdictEngine es determinista (VORTEX 2.7).

        Ejecuta el pipeline con el mismo input dos veces y verifica
        que el output es idéntico. Preserva y restaura las stats
        para no tener efectos secundarios.

        Returns:
            Dict con resultado de verificación.
        """
        test_input = {
            "text": "def hello(): print('hello world')",
            "code": "",
            "language": "python",
            "question": "Is this code safe?",
        }

        # Preservar stats para restaurarlas después (verify_determinism no debe mutar estado)
        saved_stats = {}
        with self._stats_lock:
            for attr in ("_total_verdicts", "_llm_verdicts", "_consensus_verdicts",
                         "_low_confidence_verdicts", "_fallback_verdicts",
                         "_yes_count", "_no_count", "_total_time"):
                saved_stats[attr] = getattr(self, attr, 0)

        try:
            # Ejecutar dos veces con el mismo input
            result1 = self.verdict(**test_input)
            result2 = self.verdict(**test_input)

            # Restaurar stats
            with self._stats_lock:
                for attr, val in saved_stats.items():
                    setattr(self, attr, val)

            # Comparar outputs relevantes (no timestamps ni métricas variables)
            deterministic = (
                result1.verdict == result2.verdict
                and result1.source == result2.source
                and result1.confidence == result2.confidence
            )

            return {
                "component": "VerdictEngine",
                "deterministic": deterministic,
                "verdicts_match": result1.verdict.value == result2.verdict.value,
                "sources_match": result1.source == result2.source,
                "confidence_match": result1.confidence == result2.confidence,
                "status": "VERIFIED" if deterministic else "DEGRADED",
            }
        except Exception as exc:
            # Restaurar stats incluso en error
            with self._stats_lock:
                for attr, val in saved_stats.items():
                    setattr(self, attr, val)
            return {
                "component": "VerdictEngine",
                "deterministic": False,
                "error": str(exc),
                "status": "ERROR",
            }

    def set_geodesic_tracker(self, tracker) -> None:
        """Inyecta un GeodesicTracker para rastrear la geodésica actual (VORTEX 2.5)."""
        self._geodesic_tracker = tracker

    def set_topological_router(self, router) -> None:
        """Inyecta un TopologicalRouter para redistribución topológica (VORTEX 2.4)."""
        self._topology_router = router
