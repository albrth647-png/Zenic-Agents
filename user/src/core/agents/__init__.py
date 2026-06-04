"""
ZENIC-AGENTS v18 — Single-Responsibility Agent Architecture

This is the canonical agent module for Zenic Enterprise Assistant.
Migrated from the legacy v16 multi-responsibility agents (formerly agents/)
and the experimental v18 agents (formerly agents_v2/) into a single unified
module.

Every agent has EXACTLY ONE function. No exceptions.
Qwen AI is ONLY used for binary verdicts (YES/NO) through VerdictEngine.
Everything else is 100% deterministic.

INVARIANTS:
  1. No agent may call the LLM directly. ALL LLM calls go through VerdictEngine.
  2. The LLM can only return "YES" or "NO". Any other response is treated as "NO".
  3. Every agent MUST have a deterministic fallback. The system MUST work 100% without AI.
  4. No two agents may share the same responsibility. Duplication is a design error.
  5. Every agent call is audited. Every decision has an evidence trail.
  6. Security veto is absolute. If SecurityScanner says NO, it is NO. No override possible.
"""

# Schemas & types (single source of truth for all data types)
# A2A Protocol — Agent-to-Agent interoperability
from .a2a import (
    A2AAgentCard,
    A2AClient,
    A2ADelegationPolicy,
    A2ADelegationResult,
    A2ADiscoveryResult,
    A2AResponseMessage,
    A2ATaskMessage,
    A2ATaskPriority,
)

# AG-UI Protocol — Agent-Generated UI
from .ag_ui import (
    AGUIApprovalProps,
    AGUIChartData,
    AGUIComponentSpec,
    AGUIComponentType,
    AGUIEmitter,
    AGUIEventPayload,
    AGUIFormField,
    AGUIMetricCard,
    AGUITableColumn,
)

# Layer 9: Infrastructure — AgentRunner is used by orchestrator
from .infrastructure import (
    AgentCache,
    AgentRunner,
)

# Commerce agents — Phase 1: Commerce
from .commerce import (
    CatalogManager,
    OrderManager,
    PaymentProcessor,
)

# Finance agents — Phase 2: Finance
from .finance import (
    BudgetManager,
    ExpenseTracker,
    TaxCalculator,
)

# Enterprise agents — Phase 3: Enterprise Operations
from .enterprise import (
    ComplianceChecker,
    ContractManager,
    ProjectTracker,
)

# Intelligence agents — Phase 4: Business Intelligence
from .intelligence import (
    AnomalyDetector,
    CustomerInsights,
    MarketAnalyzer,
    RiskAssessor,
    SalesForecaster,
)

# Documents agents — Phase 5: Documents & Reports
from .documents import (
    DocumentGenerator,
    ReportEngine,
    TemplateFiller,
)

# Procurement agents — Phase 6: Procurement & Vendors
from .procurement import (
    PurchaseOrderManager,
    SupplierEvaluator,
    VendorManager,
)

# Resilience patterns
from .resilience import (
    AgentBulkhead,
    AgentCircuitBreaker,
    AgentHealthSnapshot,
    AgentRetryConfig,
    AuditLogger,
    BaseAgent,
    BulkheadManager,
    CircuitBreakerManager,
    GlobalHealthMonitor,
    with_agent_retry,
)
from .schemas import (
    ActionSpec,
    AgentMessage,
    AgentResult,
    AnalyticsResult,
    AuditEntry,
    AutoDescription,
    BusinessData,
    ChainResult,
    CircuitState,
    CompressedContext,
    Conclusion,
    ConditionResult,
    ConfidenceResult,
    ConfigResult,
    ConsensusResult,
    CriticalityResult,
    CRMResult,
    DecomposedSteps,
    EntityResult,
    Evidence,
    EvidenceType,
    FixSuggestions,
    HealthSnapshot,
    IntentResult,
    InventoryResult,
    InvoiceResult,
    LanguageResult,
    MemoryEntries,
    NameResult,
    NotificationResult,
    PipelineResult,
    PrefetchResult,
    ProblemType,
    ReasoningResult,
    ReasoningStep,
    ReportResult,
    RiskResult,
    RoutedOperation,
    ScheduleSpec,
    ScoredEntries,
    ScoredEntry,
    SecurityResult,
    SyntaxResult,
    TargetResult,
    TaskResult,
    TriggerSpec,
    ValidationIssue,
    Verdict,
    VerdictInput,
    VerdictOutput,
    WorkflowSpec,
)

# Layer 10: Transport — MOVED to src.core.channels
# Lazy re-export via __getattr__ for backward compatibility
# (direct import would cause circular import: agents → channels → agents)

# Layer 1: Understanding
# Shared intent utilities (migrated from legacy agents/intent_shared.py)
from .understanding.intent_utils import (
    GOAL_KEYWORDS,
    OP_KEYWORDS,
    VALID_GOALS,
    VALID_OPERATIONS,
    extract_code_block,
    extract_entities,
    extract_target_and_language,
    infer_criticality,
    infer_template_type,
)

# Layer 8: Verdict — DeterministicPipeline is defined in verdict_parts/
# (agents/verdict/ was archived; the real implementation is in verdict_parts/)
from src.core.verdict_parts import DeterministicPipeline

__all__ = [
    "GOAL_KEYWORDS",
    "OP_KEYWORDS",
    "VALID_GOALS",
    "VALID_OPERATIONS",
    # A2A Protocol
    "A2AAgentCard",
    "A2AClient",
    "A2ADelegationPolicy",
    "A2ADelegationResult",
    "A2ADiscoveryResult",
    "A2AResponseMessage",
    "A2ATaskMessage",
    "A2ATaskPriority",
    # AG-UI Protocol
    "AGUIApprovalProps",
    "AGUIChartData",
    "AGUIComponentSpec",
    "AGUIComponentType",
    "AGUIEmitter",
    "AGUIEventPayload",
    "AGUIFormField",
    "AGUIMetricCard",
    "AGUITableColumn",
    # Enterprise
    "ComplianceChecker",
    "ContractManager",
    "ProjectTracker",
    # Finance
    "BudgetManager",
    "ExpenseTracker",
    "TaxCalculator",
    # Documents
    "DocumentGenerator",
    "ReportEngine",
    "TemplateFiller",
    # Procurement
    "PurchaseOrderManager",
    "SupplierEvaluator",
    "VendorManager",
    # Intelligence
    "AnomalyDetector",
    "CustomerInsights",
    "MarketAnalyzer",
    "RiskAssessor",
    "SalesForecaster",
    # Commerce
    "CatalogManager",
    "OrderManager",
    "PaymentProcessor",
    # Schemas & types
    "AgentResult",
    "AgentMessage",
    "AgentBulkhead",
    "AgentCache",
    "AgentCircuitBreaker",
    "AgentHealthSnapshot",
    "AgentRetryConfig",
    # Layer 9: Infrastructure
    "AgentRunner",
    # Resilience
    "BaseAgent",
    "BulkheadManager",
    "CircuitBreakerManager",
    "CircuitState",
    "GlobalHealthMonitor",
    # Layer 8: Verdict
    "DeterministicPipeline",
    # Layer 10: Transport
    "TextChannelAgent",
    "VoiceChannelAgent",
    # Shared intent utilities
    "extract_code_block",
    "extract_entities",
    "extract_target_and_language",
    "infer_criticality",
    "infer_template_type",
    "with_agent_retry",
    # Audit
    "AuditEntry",
    "AuditLogger",
]


def __getattr__(name: str):
    """Lazy import of backward-compatible names to avoid circular imports.

    ``TextChannelAgent`` and ``VoiceChannelAgent`` moved to
    ``src.core.channels``. We re-export them here for backward
    compatibility without triggering the circular import chain
    (agents → channels → agents) at module load time.
    """
    if name == "TextChannelAgent":
        from src.core.channels._text_delivery import TextChannelAgent
        return TextChannelAgent
    if name == "VoiceChannelAgent":
        from src.core.channels._voice_transcriber import VoiceChannelAgent
        return VoiceChannelAgent
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
