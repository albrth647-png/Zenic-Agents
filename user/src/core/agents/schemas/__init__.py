"""Shared schemas and types for v18 agent system."""

from ..resilience.audit_logger import AuditEntry

# Re-export from resilience (single source of truth)
from ..resilience.circuit_breaker import CircuitState

# V1 compat schemas — migrated from agents/schemas.py (legacy)
from ._v1_compat_schemas import (
    AutomationInput,
    AutomationOutput,
    BusinessInput,
    BusinessOutput,
    CodeInput,
    CodeOutput,
    ContextEntry,
    ContextInput,
    ContextOutput,
    CriticalityInput,
    CriticalityOutput,
    FileSpec,
    IntentInput,
    IntentOutput,
    ReasoningInput,
    ReasoningOutput,
    ValidationInput,
    ValidationOutput,
)
from ._v1_compat_schemas import (
    ReasoningStep as V1ReasoningStep,
)
from .types import (
    ActionSpec,
    AgentMessage,
    # Base types
    AgentResult,
    AnalyticsResult,
    # Layer 6: Automation
    AutoDescription,
    # Layer 3: Business
    BusinessData,
    ChainResult,
    # Layer 4: Code
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
    # Layer 9: Infrastructure
    HealthSnapshot,
    # Layer 1: Understanding
    IntentResult,
    InventoryResult,
    InvoiceResult,
    LanguageResult,
    # Layer 2: Memory & Context
    MemoryEntries,
    NameResult,
    NotificationResult,
    PipelineResult,
    PrefetchResult,
    # Layer 7: Reasoning
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
    # Layer 5: Validation
    SecurityResult,
    SyntaxResult,
    TargetResult,
    TaskResult,
    # Layer 10: Transport
    TextChannelInput,
    TextChannelResult,
    TriggerSpec,
    ValidationIssue,
    # Layer 8: Verdict
    Verdict,
    VerdictInput,
    VerdictOutput,
    VoiceChannelInput,
    VoiceChannelResult,
    WorkflowSpec,
)

__all__ = [
    "ActionSpec",
    "AgentMessage",
    # Base types
    "AgentResult",
    "AnalyticsResult",
    "AuditEntry",
    # Layer 6: Automation
    "AutoDescription",
    "AutomationInput",
    "AutomationOutput",
    # Layer 3: Business
    "BusinessData",
    "BusinessInput",
    "BusinessOutput",
    "CRMResult",
    "ChainResult",
    # Re-exported from resilience
    "CircuitState",
    "CodeInput",
    "CodeOutput",
    # Layer 4: Code
    "CodeRequest",
    "CodeResult",
    "CompressedContext",
    "Conclusion",
    "ConditionResult",
    "ConfidenceResult",
    "ConfigResult",
    "ConsensusResult",
    "ContextEntry",
    "ContextInput",
    "ContextOutput",
    "CriticalityInput",
    "CriticalityOutput",
    "CriticalityResult",
    "DecomposedSteps",
    "EntityResult",
    "Evidence",
    "EvidenceType",
    "FileSpec",
    "FixSuggestions",
    # Layer 9: Infrastructure
    "HealthSnapshot",
    # V1 compat schemas
    "IntentInput",
    "IntentOutput",
    # Layer 1: Understanding
    "IntentResult",
    "InventoryResult",
    "InvoiceResult",
    "LanguageResult",
    # Layer 2: Memory & Context
    "MemoryEntries",
    "NameResult",
    "NotificationResult",
    "PipelineResult",
    "PrefetchResult",
    # Layer 7: Reasoning
    "ProblemType",
    "ReasoningInput",
    "ReasoningOutput",
    "ReasoningResult",
    "ReasoningStep",
    "ReportResult",
    "RiskResult",
    "RoutedOperation",
    "ScaffoldResult",
    "ScheduleSpec",
    "ScoredEntries",
    "ScoredEntry",
    # Layer 5: Validation
    "SecurityResult",
    "SyntaxResult",
    "TargetResult",
    "TaskResult",
    # Layer 10: Transport
    "TextChannelInput",
    "TextChannelResult",
    "TriggerSpec",
    "V1ReasoningStep",
    "ValidationInput",
    "ValidationIssue",
    "ValidationOutput",
    # Layer 8: Verdict
    "Verdict",
    "VerdictInput",
    "VerdictOutput",
    "VoiceChannelInput",
    "VoiceChannelResult",
    "WorkflowSpec",
]
