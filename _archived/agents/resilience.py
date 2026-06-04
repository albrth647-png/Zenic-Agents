"""
ZENIC-AGENTS — Resilience stubs (standalone mode).

When the full src/ tree is not available, these minimal stubs provide
the BaseAgent contract and CircuitBreaker types needed by _archived agents.

All methods are deterministic no-ops by design — the system works 100%
without AI or external infrastructure.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class CircuitBreakerState:
    """Minimal circuit breaker (CLOSED/OPEN/HALF_OPEN)."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state: str = self.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.lock = threading.Lock()


class CircuitBreakerManager:
    """Minimal circuit breaker manager — always allows calls."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreakerState] = {}

    def can_call(self, name: str) -> bool:
        return True

    def record_success(self, name: str) -> None:
        pass

    def record_failure(self, name: str) -> None:
        pass

    def reset(self, name: str) -> None:
        pass

    def stats(self) -> dict[str, Any]:
        return {}


class _AgentHealthSnapshot:
    """Minimal per-agent health snapshot stub."""

    def __init__(self, agent_name: str = "") -> None:
        self.agent_name = agent_name
        self.total_calls: int = 0
        self.successful_calls: int = 0
        self.failed_calls: int = 0
        self.healthy: bool = True
        self.success_rate: float = 1.0
        self.avg_latency_s: float = 0.0
        self.last_call_time: float = 0.0


class GlobalHealthMonitor:
    """Minimal health monitor stub."""

    def __init__(self) -> None:
        self._snapshots: dict[str, _AgentHealthSnapshot] = {}
        self._records: list[dict[str, Any]] = []

    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy"}

    def system_health(self) -> dict[str, Any]:
        """Return system-wide health status."""
        return {
            "healthy": True,
            "unhealthy_agents": [],
            "warning_agents": [],
        }

    def all_snapshots(self) -> dict[str, _AgentHealthSnapshot]:
        """Return all per-agent snapshots."""
        return dict(self._snapshots)

    def get_snapshot(self, agent_name: str) -> _AgentHealthSnapshot:
        """Return snapshot for a specific agent (creates if missing)."""
        if agent_name not in self._snapshots:
            self._snapshots[agent_name] = _AgentHealthSnapshot(agent_name)
        return self._snapshots[agent_name]

    def record_call(
        self,
        agent_name: str,
        success: bool,
        latency_s: float,
        was_timeout: bool = False,
    ) -> None:
        """Record an agent call result."""
        snap = self.get_snapshot(agent_name)
        snap.total_calls += 1
        if success:
            snap.successful_calls += 1
        else:
            snap.failed_calls += 1
        snap.success_rate = snap.successful_calls / max(snap.total_calls, 1)
        snap.avg_latency_s = latency_s
        snap.last_call_time = time.monotonic()
        self._records.append({
            "agent_name": agent_name,
            "success": success,
            "latency_s": latency_s,
            "was_timeout": was_timeout,
            "timestamp": time.monotonic(),
        })

    def is_healthy(self, agent_name: str) -> bool:
        """Quick health check for a specific agent."""
        return self.get_snapshot(agent_name).healthy


@dataclass
class AuditEntry:
    agent: str = ""
    input_hash: str = ""
    output_hash: str = ""
    source: str = "deterministic"
    confidence: float = 0.0
    duration_ms: float = 0.0
    retry_count: int = 0
    circuit_breaker_state: str = "CLOSED"
    evidence_summary: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "source": self.source,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "circuit_breaker_state": self.circuit_breaker_state,
            "evidence_summary": self.evidence_summary,
            "timestamp": self.timestamp,
        }


class AuditLogger:
    """Minimal audit logger stub."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, entry: AuditEntry | dict[str, Any]) -> None:
        if isinstance(entry, AuditEntry):
            self._entries.append(entry)
        elif isinstance(entry, dict):
            self._entries.append(AuditEntry(**{k: v for k, v in entry.items() if k in AuditEntry.__dataclass_fields__}))

    def get_recent(
        self, agent_name: str | None = None, count: int = 10
    ) -> list[AuditEntry]:
        entries = self._entries
        if agent_name:
            entries = [e for e in entries if e.agent == agent_name]
        return entries[-count:]

    def get_failure_pattern(
        self, agent_name: str | None = None
    ) -> dict[str, Any]:
        return {"pattern": "none", "agent_name": agent_name or ""}

    @property
    def stats(self) -> dict[str, Any]:
        return {"total_entries": len(self._entries)}

    @staticmethod
    def hash_data(data: Any) -> str:
        if data is None:
            return ""
        return str(hash(str(data)))


class BaseAgent:
    """
    Minimal BaseAgent stub for standalone mode.

    Every agent has exactly ONE responsibility, implemented in execute().
    The system works 100% without AI — fallback() is always deterministic.

    Subclasses should override:
      - execute(input_data) -> T
      - fallback(input_data) -> T
    """

    name: str
    __orig_bases__: ClassVar[tuple] = ()

    def __class_getitem__(cls, item):
        """Support BaseAgent[T] generic subscript syntax at runtime."""
        return cls

    def __init__(self, name: str = "BaseAgent", **kwargs: Any) -> None:
        self.name = name
        self._cb_manager = CircuitBreakerManager()
        self._audit_logger = AuditLogger()
        self._health_monitor = GlobalHealthMonitor()

    def execute(self, input_data: Any) -> Any:
        """Override in subclass. Default: return None."""
        return None

    def fallback(self, input_data: Any) -> Any:
        """Override in subclass. Default: return None."""
        return None

    def run(self, input_data: Any) -> Any:
        """Resilient run: execute() with circuit breaker, fallback on failure."""
        if not self._cb_manager.can_call(self.name):
            return self.fallback(input_data)
        try:
            result = self.execute(input_data)
            self._cb_manager.record_success(self.name)
            return result
        except Exception:
            self._cb_manager.record_failure(self.name)
            return self.fallback(input_data)

    def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": "healthy",
        }

    def wire(self, **kwargs: Any) -> None:
        """Wire external dependencies (optional)."""
        pass

    @property
    def is_wired(self) -> bool:
        return False


# ── Singleton helpers ──────────────────────────────────────────

def get_global_health_monitor() -> GlobalHealthMonitor:
    return GlobalHealthMonitor()
