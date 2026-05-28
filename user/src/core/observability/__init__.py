"""
ZENIC-AGENTS v16 - Observability Module (Phase 5)

Comprehensive observability stack:
- OpenTelemetry-compatible tracing with Jaeger export
- Prometheus metrics with standard client library
- Structured audit logging with trace correlation
- Health check aggregation for all subsystems

All components are optional — graceful degradation when
dependencies are not installed (e.g. on Termux/ARM).
"""

from .audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditSeverity,
    get_audit_logger,
)
from .forensic import (
    ChainVerificationResult,
    EvidenceBundle,
    ForensicEngine,
    ForensicEntry,
    ForensicReport,
    get_forensic_engine,
    reset_forensic_engine,
)
from .health import (
    HealthAggregator,
    HealthCheckResult,
    HealthStatus,
    check_auth_db,
    check_coordination_backend,
    check_disk_space,
    check_orchestrator,
    check_redis,
    check_resources,
    get_health_aggregator,
)
from .metrics import (
    MetricsCollector,
    MetricsConfig,
    get_metrics_collector,
    metrics_middleware,
)
from .snapshot_audit import (
    SnapshotAuditEngine,
    SnapshotDiff,
    SnapshotEntry,
    SnapshotPair,
    get_snapshot_audit_engine,
    reset_snapshot_audit_engine,
)
from .tracing import (
    TracingConfig,
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    init_tracing,
    inject_trace_context,
    trace_span,
)

__all__ = [
    "AuditEvent",
    "AuditEventType",
    # Audit
    "AuditLogger",
    "AuditSeverity",
    "ChainVerificationResult",
    "EvidenceBundle",
    # Forensic
    "ForensicEngine",
    "ForensicEntry",
    "ForensicReport",
    # Health
    "HealthAggregator",
    "HealthCheckResult",
    "HealthStatus",
    # Metrics
    "MetricsCollector",
    "MetricsConfig",
    # Snapshot Audit
    "SnapshotAuditEngine",
    "SnapshotDiff",
    "SnapshotEntry",
    "SnapshotPair",
    # Tracing
    "TracingConfig",
    "check_auth_db",
    "check_coordination_backend",
    "check_disk_space",
    "check_orchestrator",
    "check_redis",
    "check_resources",
    "extract_trace_context",
    "get_audit_logger",
    "get_current_span_id",
    "get_current_trace_id",
    "get_forensic_engine",
    "get_health_aggregator",
    "get_metrics_collector",
    "get_snapshot_audit_engine",
    "get_tracer",
    "init_tracing",
    "inject_trace_context",
    "metrics_middleware",
    "reset_forensic_engine",
    "reset_snapshot_audit_engine",
    "trace_span",
]
