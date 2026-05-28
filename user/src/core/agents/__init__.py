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
# Layer 6: Automation
from .automation import (
    ActionInferrer,
    AutomationNamer,
    ConditionExtractor,
    ScheduleParser,
    TriggerInferrer,
    WorkflowSerializer,
)

# Layer 3: Business
from .business import (
    CRMPipeline,
    DataAnalyzer,
    InventoryManager,
    InvoiceProcessor,
    NotificationDispatcher,
    OperationRouter,
    ReportGenerator,
    TaskScheduler,
)

# Layer 9: Infrastructure
from .infrastructure import (
    AgentCache,
    AgentRunner,
    AuditLoggerAgent,
    CircuitBreakerManagerAgent,
    HealthMonitorAgent,
)

# Layer 2: Memory & Context
from .memory import (
    ContextCompressor,
    ContextPrefetcher,
    MemoryCollector,
    RelevanceScorer,
)

# Layer 7: Reasoning
from .reasoning import (
    ConclusionExtractor,
    ConfidenceEstimator,
    ProblemDetector,
    StepDecomposer,
    TemplateReasoner,
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
    CodeRequest,
    CodeResult,
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
    ScaffoldResult,
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

# Layer 10: Transport
from .transport import (
    TextChannelAgent,
    VoiceChannelAgent,
)

# Layer 1: Understanding
from .understanding import (
    BilingualRouter,
    CriticalityScorer,
    EntityExtractor,
    IntentClassifier,
    TargetResolver,
)

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

# Layer 4: Code — REMOVED (code_ops module deleted; code generation is not part of assistant-agent)
# CodeGenerator, CodeRefactorer, CodeOptimizer, CodeFixer,
# ProjectScaffolder, DefensiveInjector no longer available
# Layer 5: Validation & Security
from .validation import (
    ChainValidator,
    ConfigValidator,
    FixSuggester,
    RiskCalculator,
    SecurityScanner,
    SyntaxValidator,
)

# Layer 8: Verdict
from .verdict import (
    ConsensusResolverV18,
    DeterministicPipeline,
    EvidenceCollectorV18,
    VerdictEngineV18,
)

__all__ = [
    "GOAL_KEYWORDS",
    "OP_KEYWORDS",
    "VALID_GOALS",
    "VALID_OPERATIONS",
    "ActionInferrer",
    "ActionSpec",
    "AgentBulkhead",
    "AgentCache",
    "AgentCircuitBreaker",
    "AgentHealthSnapshot",
    "AgentMessage",
    # Schemas & types
    "AgentResult",
    "AgentRetryConfig",
    # Layer 9: Infrastructure
    "AgentRunner",
    "AnalyticsResult",
    "AuditEntry",
    "AuditLogger",
    "AuditLoggerAgent",
    "AutoDescription",
    "AutomationNamer",
    # Resilience
    "BaseAgent",
    "BilingualRouter",
    "BulkheadManager",
    "BusinessData",
    "CRMPipeline",
    "CRMResult",
    "ChainResult",
    "ChainValidator",
    "CircuitBreakerManager",
    "CircuitBreakerManagerAgent",
    "CircuitState",
    # CodeResult types retained in schemas for backward compatibility
    "CodeRequest",
    "CodeResult",
    "CompressedContext",
    "Conclusion",
    "ConclusionExtractor",
    "ConditionExtractor",
    "ConditionResult",
    "ConfidenceEstimator",
    "ConfidenceResult",
    "ConfigResult",
    "ConfigValidator",
    "ConsensusResolverV18",
    "ConsensusResult",
    "ContextCompressor",
    "ContextPrefetcher",
    "CriticalityResult",
    "CriticalityScorer",
    "DataAnalyzer",
    "DecomposedSteps",
    # Layer 8: Verdict
    "DeterministicPipeline",
    "EntityExtractor",
    "EntityResult",
    "Evidence",
    "EvidenceCollectorV18",
    "EvidenceType",
    "FixSuggester",
    "FixSuggestions",
    "GlobalHealthMonitor",
    "HealthMonitorAgent",
    "HealthSnapshot",
    # Layer 1: Understanding
    "IntentClassifier",
    "IntentResult",
    "InventoryManager",
    "InventoryResult",
    # Layer 3: Business
    "InvoiceProcessor",
    "InvoiceResult",
    "LanguageResult",
    # Layer 2: Memory & Context
    "MemoryCollector",
    "MemoryEntries",
    "NameResult",
    "NotificationDispatcher",
    "NotificationResult",
    "OperationRouter",
    "PipelineResult",
    "PrefetchResult",
    # Layer 7: Reasoning
    "ProblemDetector",
    "ProblemType",
    "ReasoningResult",
    "ReasoningStep",
    "RelevanceScorer",
    "ReportGenerator",
    "ReportResult",
    "RiskCalculator",
    "RiskResult",
    "RoutedOperation",
    "ScaffoldResult",
    "ScheduleParser",
    "ScheduleSpec",
    "ScoredEntries",
    "ScoredEntry",
    "SecurityResult",
    # Layer 4: Code — REMOVED (code_ops deleted)
    # "CodeGenerator", "CodeRefactorer", "CodeOptimizer", "CodeFixer",
    # "ProjectScaffolder", "DefensiveInjector",
    # Layer 5: Validation & Security
    "SecurityScanner",
    "StepDecomposer",
    "SyntaxResult",
    "SyntaxValidator",
    "TargetResolver",
    "TargetResult",
    "TaskResult",
    "TaskScheduler",
    "TemplateReasoner",
    # Layer 10: Transport
    "TextChannelAgent",
    # Layer 6: Automation
    "TriggerInferrer",
    "TriggerSpec",
    "ValidationIssue",
    "Verdict",
    "VerdictEngineV18",
    "VerdictInput",
    "VerdictOutput",
    "VoiceChannelAgent",
    "WorkflowSerializer",
    "WorkflowSpec",
    # Shared intent utilities
    "extract_code_block",
    "extract_entities",
    "extract_target_and_language",
    "infer_criticality",
    "infer_template_type",
    "with_agent_retry",
]
