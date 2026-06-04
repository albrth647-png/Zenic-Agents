"""
BaseAgent for v18 Single-Responsibility Architecture.

Every agent inherits from BaseAgent and implements EXACTLY ONE function.
All agents are deterministic by default. Only VerdictEngine uses AI.

INVARIANTS:
  1. No agent may call the LLM directly.
  2. Every agent MUST have a deterministic execute() method.
  3. Every agent call is wrapped with circuit breaker + retry + bulkhead.
  4. Every agent call is audited.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Generic, TypeVar

from .audit_logger import AuditEntry, AuditLogger
from .bulkhead import BulkheadManager
from .circuit_breaker import CircuitBreakerManager
from .health_monitor import GlobalHealthMonitor
from .retry import AgentRetryConfig

T = TypeVar("T")


class BaseAgent(Generic[T]):
    """
    Abstract base class for all v18 agents.

    NATURALEZA ONTOLÓGICA:
      SOY: La plantilla ontológica para todos los agentes del sistema. Cada agente
           tiene EXACTAMENTE UNA responsabilidad, implementada en execute(). Todos
           los agentes son determinísticos por defecto. El patrón de resiliencia
           (circuit breaker, bulkhead, retry, auditoría) se aplica automáticamente.
      NO SOY: Framework de agentes genérico. No permito que los agentes llamen al
              LLM directamente. No soporto herencia múltiple de responsabilidades.
      INVARIANTE: El sistema funciona 100% sin IA. Cada agente tiene un fallback()
                  determinístico que nunca falla.
      FRONTERA: Un agente no puede llamar a otro agente. Solo el orquestador
                coordina agentes.

    COMPLETACIÓN SEMÁNTICA:
      - CircuitBreaker produce PROTECCIÓN (puerta abierta/cerrada)
      - Mi run() completa esa protección con RECUPERACIÓN: si el breaker está
        abierto, ejecuto fallback() en lugar de execute().
      - Yo produzco EJECUCIÓN RESILIENTE; el orquestador produce COORDINACIÓN.

    Each agent has EXACTLY ONE responsibility, implemented in execute().
    All resilience patterns are applied automatically.
    """

    def __init__(
        self,
        name: str,
        circuit_breaker_manager: CircuitBreakerManager | None = None,
        bulkhead_manager: BulkheadManager | None = None,
        health_monitor: GlobalHealthMonitor | None = None,
        audit_logger: AuditLogger | None = None,
        retry_config: AgentRetryConfig | None = None,
    ) -> None:
        self.name = name
        self._cb_manager = circuit_breaker_manager or CircuitBreakerManager()
        self._bulkhead_manager = bulkhead_manager or BulkheadManager()
        self._health_monitor = health_monitor or GlobalHealthMonitor()
        self._audit_logger = audit_logger or AuditLogger()
        self._retry_config = retry_config or AgentRetryConfig()

        # Thread-safe stats
        self._stats_lock = threading.Lock()
        self._call_count = 0
        self._success_count = 0
        self._fallback_count = 0
        self._total_duration_ms = 0.0
        self._last_error = ""

    def execute(self, input_data: Any) -> T:
        """
        The ONE function this agent performs.

        MUST be overridden by every concrete agent.
        MUST be deterministic (no AI calls).
        MUST always return a valid result (never raises).
        """
        raise NotImplementedError(f"Agent {self.name} must implement execute() with exactly ONE responsibility")

    def fallback(self, input_data: Any) -> T:
        """
        Deterministic fallback when execute() fails.
        MUST be overridden. MUST always succeed.
        """
        raise NotImplementedError(f"Agent {self.name} must implement fallback()")

    def run(self, input_data: Any) -> dict[str, Any]:
        """
        Run the agent with full resilience:
        1. Check circuit breaker
        2. Acquire bulkhead slot
        3. Execute with retry
        4. Fallback on failure
        5. Audit the result
        6. Report to health monitor
        """
        start_time = time.monotonic()
        result = None
        source = "deterministic"
        retry_count = 0
        error = ""

        # 1. Circuit breaker check
        if not self._cb_manager.can_call(self.name):
            source = "circuit_open_fallback"
            try:
                result = self.fallback(input_data)
            except Exception as e:
                error = str(e)
            self._record_run(start_time, source, result is not None, error, retry_count)
            return self._format_result(result, source, start_time, retry_count)

        # 2. Bulkhead
        bulkhead = self._bulkhead_manager.get_bulkhead(self.name)
        if not bulkhead.acquire(timeout=5.0):
            source = "bulkhead_fallback"
            try:
                result = self.fallback(input_data)
            except Exception as e:
                error = str(e)
            self._record_run(start_time, source, result is not None, error, retry_count)
            return self._format_result(result, source, start_time, retry_count)

        try:
            # 3. Execute with retry
            for attempt in range(1, self._retry_config.max_attempts + 1):
                try:
                    result = self.execute(input_data)
                    source = "deterministic"
                    break
                except Exception as e:
                    error = str(e)
                    retry_count = attempt
                    if attempt < self._retry_config.max_attempts:
                        delay = self._retry_config.compute_delay(attempt)
                        time.sleep(delay)
            else:
                # All retries exhausted → fallback
                try:
                    result = self.fallback(input_data)
                    source = "fallback"
                    error = ""
                except Exception as e:
                    error = str(e)
                    source = "error"

        finally:
            bulkhead.release()

        # 5. Record success/failure for circuit breaker
        # Three categories:
        #   - Success: execute() completed → CB success
        #   - Degraded: fallback/circuit_open/bulkhead → NOT a CB failure
        #     (fallback is a successful recovery; CB/bulkhead fallback is
        #      caused by resilience itself, not agent failure)
        #   - Hard failure: execute() raised after all retries → CB failure
        if source == "deterministic":
            self._cb_manager.record_success(self.name)
            success = True
        elif source in ("error",):
            self._cb_manager.record_failure(self.name)
            success = False
        else:
            # Degraded success: fallback, circuit_open_fallback, bulkhead_fallback
            # Do NOT record as CB failure — prevents death spiral
            success = True  # Fallback is a successful recovery

        # 6. Audit + Health
        self._record_run(start_time, source, success, error, retry_count)

        return self._format_result(result, source, start_time, retry_count)

    def _record_run(
        self,
        start_time: float,
        source: str,
        success: bool,
        error: str,
        retry_count: int,
    ) -> None:
        """Record stats, health, and audit."""
        duration_ms = (time.monotonic() - start_time) * 1000

        with self._stats_lock:
            self._call_count += 1
            if success:
                self._success_count += 1
            if "fallback" in source:
                self._fallback_count += 1
            self._total_duration_ms += duration_ms
            if error:
                self._last_error = error

        # Health monitor
        self._health_monitor.record_call(
            agent_name=self.name,
            success=success,
            latency_s=duration_ms / 1000,
            was_timeout="timeout" in error.lower(),
        )

        # Audit
        cb_state = self._cb_manager.get_breaker(self.name).state.value
        self._audit_logger.record(
            AuditEntry(
                agent=self.name,
                source=source,
                duration_ms=duration_ms,
                retry_count=retry_count,
                circuit_breaker_state=cb_state,
                evidence_summary=error[:200] if error else "",
            )
        )

    def _format_result(
        self,
        result: Any,
        source: str,
        start_time: float,
        retry_count: int,
    ) -> dict[str, Any]:
        """Format result into standard envelope."""
        duration_ms = (time.monotonic() - start_time) * 1000
        return {
            "success": result is not None,
            "data": result,
            "source": source,
            "duration_ms": duration_ms,
            "retry_count": retry_count,
            "agent": self.name,
        }

    @property
    def stats(self) -> dict[str, Any]:
        with self._stats_lock:
            avg_duration = self._total_duration_ms / self._call_count if self._call_count > 0 else 0.0
            success_rate = self._success_count / self._call_count if self._call_count > 0 else 1.0
            return {
                "name": self.name,
                "call_count": self._call_count,
                "success_count": self._success_count,
                "fallback_count": self._fallback_count,
                "success_rate": success_rate,
                "avg_duration_ms": avg_duration,
                "last_error": self._last_error,
            }

    # ================================================================
    #  VORTEX 2.7: Auto-verificación de determinismo
    # ================================================================

    def verify_determinism(self) -> dict[str, Any]:
        """
        Verifica que el agente concreto (subclase) es determinista (VORTEX 2.7).

        NOTA: BaseAgent es abstracta. Esta verificación solo es significativa
        cuando se llama desde una SUBCLASE concreta que implementa execute().
        Si se llama desde la clase base, reportará "ABSTRACT" en el status.

        Prueba que execute() produce el mismo output para el mismo input
        y que fallback() nunca falla.

        Returns:
            Dict con resultado de verificación.
        """
        test_input = {"test": "verify_determinism"}
        is_abstract = False

        try:
            # Verificar que fallback() nunca falla
            fallback_result = self.fallback(test_input)
            fallback_ok = fallback_result is not None
        except NotImplementedError:
            is_abstract = True
            fallback_ok = False
        except Exception:
            fallback_ok = False

        try:
            # Verificar determinismo: mismo input → mismo output
            result1 = self.execute(test_input)
            result2 = self.execute(test_input)
            deterministic = result1 == result2
        except NotImplementedError:
            is_abstract = True
            deterministic = False
        except Exception:
            deterministic = False

        if is_abstract:
            status = "ABSTRACT"
        elif deterministic and fallback_ok:
            status = "VERIFIED"
        else:
            status = "DEGRADED"

        return {
            "component": f"BaseAgent.{self.name}",
            "deterministic": deterministic,
            "fallback_available": fallback_ok,
            "is_abstract": is_abstract,
            "status": status,
        }
