"""
Phase A-C imports: Observability, Events, Workflows, Exceptions.

Split from src/core/__init__.py for maintainability.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Phase A: Observability ────────────────────────────────
try:
    from src.core.observability import (
        AuditEvent,
        AuditEventType,
        AuditLogger,
        AuditSeverity,
        ChainVerificationResult,
        EvidenceBundle,
        ForensicEngine,
        ForensicEntry,
        ForensicReport,
        HealthAggregator,
        HealthCheckResult,
        HealthStatus,
        MetricsCollector,
        MetricsConfig,
        SnapshotAuditEngine,
        SnapshotDiff,
        SnapshotEntry,
        SnapshotPair,
        TracingConfig,
        get_audit_logger,
        get_forensic_engine,
        get_health_aggregator,
        get_metrics_collector,
        get_snapshot_audit_engine,
        get_tracer,
        init_tracing,
        trace_span,
    )
except ImportError as exc:
    logger.warning("core: Observability import failed: %s", exc)
    ForensicEngine = None  # type: ignore[misc,assignment]
    ForensicEntry = None  # type: ignore[misc,assignment]
    ForensicReport = None  # type: ignore[misc,assignment]
    ChainVerificationResult = None  # type: ignore[misc,assignment]
    EvidenceBundle = None  # type: ignore[misc,assignment]
    get_forensic_engine = None  # type: ignore[misc,assignment]
    SnapshotAuditEngine = None  # type: ignore[misc,assignment]
    SnapshotEntry = None  # type: ignore[misc,assignment]
    SnapshotPair = None  # type: ignore[misc,assignment]
    SnapshotDiff = None  # type: ignore[misc,assignment]
    get_snapshot_audit_engine = None  # type: ignore[misc,assignment]
    AuditLogger = None  # type: ignore[misc,assignment]
    AuditEvent = None  # type: ignore[misc,assignment]
    AuditEventType = None  # type: ignore[misc,assignment]
    AuditSeverity = None  # type: ignore[misc,assignment]
    get_audit_logger = None  # type: ignore[misc,assignment]
    HealthAggregator = None  # type: ignore[misc,assignment]
    HealthStatus = None  # type: ignore[misc,assignment]
    HealthCheckResult = None  # type: ignore[misc,assignment]
    get_health_aggregator = None  # type: ignore[misc,assignment]
    MetricsCollector = None  # type: ignore[misc,assignment]
    MetricsConfig = None  # type: ignore[misc,assignment]
    get_metrics_collector = None  # type: ignore[misc,assignment]
    TracingConfig = None  # type: ignore[misc,assignment]
    init_tracing = None  # type: ignore[misc,assignment]
    get_tracer = None  # type: ignore[misc,assignment]
    trace_span = None  # type: ignore[misc,assignment]

# ── Phase B: Events ───────────────────────────────────────
try:
    from src.core.events import (
        BatchRetryResult,
        DeadLetterEvent,
        DeadLetterStatus,
        EventSchema,
        # WebhookIngestionEngine removed — external API connection deleted
        EventSchemaRegistry,
        IssueType,
        ReplayQueue,
        RetryResult,
        TriggerCondition,
        TriggerMap,
        TriggerMapping,
        ValidationIssue,
        get_replay_queue,
        get_schema_registry,
        get_trigger_map,
    )
    from src.core.events import (
        ConditionOperator as EventConditionOperator,
    )
    from src.core.events import (
        ValidationResult as EventValidationResult,
    )
except ImportError as exc:
    logger.warning("core: Events import failed: %s", exc)
    TriggerMap = None  # type: ignore[misc,assignment]
    TriggerMapping = None  # type: ignore[misc,assignment]
    TriggerCondition = None  # type: ignore[misc,assignment]
    EventConditionOperator = None  # type: ignore[misc,assignment]
    get_trigger_map = None  # type: ignore[misc,assignment]
    # WebhookIngestionEngine removed — external API connection deleted
    EventSchemaRegistry = None  # type: ignore[misc,assignment]
    EventSchema = None  # type: ignore[misc,assignment]
    EventValidationResult = None  # type: ignore[misc,assignment]
    ValidationIssue = None  # type: ignore[misc,assignment]
    IssueType = None  # type: ignore[misc,assignment]
    get_schema_registry = None  # type: ignore[misc,assignment]
    ReplayQueue = None  # type: ignore[misc,assignment]
    DeadLetterEvent = None  # type: ignore[misc,assignment]
    DeadLetterStatus = None  # type: ignore[misc,assignment]
    RetryResult = None  # type: ignore[misc,assignment]
    BatchRetryResult = None  # type: ignore[misc,assignment]
    get_replay_queue = None  # type: ignore[misc,assignment]

# ── Phase B: Workflows ────────────────────────────────────
try:
    from src.core.workflows import (
        BranchCondition,
        BranchRule,
        ChainExecutionResult,
        ChainStep,
        ChainStepResult,
        ChainTemplate,
        ChainTemplateLibrary,
        ChainValidationResult,
        ComposedChain,
        ConditionalBranching,
        DynamicChainComposer,
        FieldMapping,
        HandoffResult,
        HandoffRule,
        InterWorkflowHandoff,
        TemplateCategory,
        TemplateStep,
        TemplateVariable,
        get_chain_composer,
        get_conditional_branching,
        get_inter_workflow_handoff,
        get_template_library,
    )
except ImportError as exc:
    logger.warning("core: Workflows import failed: %s", exc)
    DynamicChainComposer = None  # type: ignore[misc,assignment]
    ComposedChain = None  # type: ignore[misc,assignment]
    ChainStep = None  # type: ignore[misc,assignment]
    ChainStepResult = None  # type: ignore[misc,assignment]
    ChainExecutionResult = None  # type: ignore[misc,assignment]
    ChainValidationResult = None  # type: ignore[misc,assignment]
    get_chain_composer = None  # type: ignore[misc,assignment]
    ChainTemplateLibrary = None  # type: ignore[misc,assignment]
    ChainTemplate = None  # type: ignore[misc,assignment]
    TemplateStep = None  # type: ignore[misc,assignment]
    TemplateVariable = None  # type: ignore[misc,assignment]
    TemplateCategory = None  # type: ignore[misc,assignment]
    get_template_library = None  # type: ignore[misc,assignment]
    InterWorkflowHandoff = None  # type: ignore[misc,assignment]
    HandoffRule = None  # type: ignore[misc,assignment]
    HandoffResult = None  # type: ignore[misc,assignment]
    FieldMapping = None  # type: ignore[misc,assignment]
    get_inter_workflow_handoff = None  # type: ignore[misc,assignment]
    ConditionalBranching = None  # type: ignore[misc,assignment]
    BranchRule = None  # type: ignore[misc,assignment]
    BranchCondition = None  # type: ignore[misc,assignment]
    get_conditional_branching = None  # type: ignore[misc,assignment]

# ── Phase C: Exceptions ───────────────────────────────────
try:
    from src.core.exceptions import (
        AnalyticsSnapshot,
        ExceptionAnalytics,
        ExceptionCategory,
        ExceptionContext,
        ExceptionEngine,
        ExceptionPattern,
        ExceptionRecord,
        ExceptionRouter,
        ExceptionSeverity,
        ExceptionSignal,
        RoutingAction,
        RoutingRule,
        ZenicException,
        get_exception_analytics,
        get_exception_engine,
        get_exception_router,
    )
except ImportError as exc:
    logger.warning("core: Exceptions import failed: %s", exc)
    ExceptionCategory = None  # type: ignore[misc,assignment]
    ExceptionSeverity = None  # type: ignore[misc,assignment]
    ZenicException = None  # type: ignore[misc,assignment]
    ExceptionContext = None  # type: ignore[misc,assignment]
    ExceptionEngine = None  # type: ignore[misc,assignment]
    ExceptionSignal = None  # type: ignore[misc,assignment]
    ExceptionRecord = None  # type: ignore[misc,assignment]
    get_exception_engine = None  # type: ignore[misc,assignment]
    ExceptionRouter = None  # type: ignore[misc,assignment]
    RoutingRule = None  # type: ignore[misc,assignment]
    RoutingAction = None  # type: ignore[misc,assignment]
    get_exception_router = None  # type: ignore[misc,assignment]
    ExceptionAnalytics = None  # type: ignore[misc,assignment]
    ExceptionPattern = None  # type: ignore[misc,assignment]
    AnalyticsSnapshot = None  # type: ignore[misc,assignment]
    get_exception_analytics = None  # type: ignore[misc,assignment]
