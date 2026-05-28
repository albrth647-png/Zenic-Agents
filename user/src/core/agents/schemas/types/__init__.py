"""All shared data types for v18 single-responsibility agents."""

from ._advanced_types import (
    ActionSpec,
    # Layer 6: Automation
    AutoDescription,
    ChainResult,
    # Layer 4: Code
    CodeRequest,
    CodeResult,
    Conclusion,
    ConditionResult,
    ConfidenceResult,
    ConfigResult,
    ConsensusResult,
    DecomposedSteps,
    Evidence,
    EvidenceType,
    FixSuggestions,
    # Layer 9: Infrastructure
    HealthSnapshot,
    NameResult,
    PipelineResult,
    # Layer 7: Reasoning
    ProblemType,
    ReasoningResult,
    ReasoningStep,
    RiskResult,
    ScaffoldResult,
    ScheduleSpec,
    SecurityResult,
    SyntaxResult,
    TriggerSpec,
    # Layer 5: Validation
    ValidationIssue,
    # Layer 8: Verdict
    Verdict,
    VerdictInput,
    VerdictOutput,
    WorkflowSpec,
)
from ._core_types import (
    AgentMessage,
    # Base types
    AgentResult,
    AnalyticsResult,
    # Layer 3: Business
    BusinessData,
    CompressedContext,
    CriticalityResult,
    CRMResult,
    EntityResult,
    IntentResult,
    InventoryResult,
    InvoiceResult,
    # Layer 1: Understanding
    LanguageResult,
    # Layer 2: Memory & Context
    MemoryEntries,
    NotificationResult,
    PrefetchResult,
    ReportResult,
    RoutedOperation,
    ScoredEntries,
    ScoredEntry,
    TargetResult,
    TaskResult,
)
from ._transport_types import (
    # Layer 10: Transport
    TextChannelInput,
    TextChannelResult,
    VoiceChannelInput,
    VoiceChannelResult,
)

__all__ = [
    "ActionSpec",
    "AgentMessage",
    # Base types
    "AgentResult",
    "AnalyticsResult",
    # Layer 6: Automation
    "AutoDescription",
    # Layer 3: Business
    "BusinessData",
    "CRMResult",
    "ChainResult",
    # Layer 4: Code
    "CodeRequest",
    "CodeResult",
    "CompressedContext",
    "Conclusion",
    "ConditionResult",
    "ConfidenceResult",
    "ConfigResult",
    "ConsensusResult",
    "CriticalityResult",
    "DecomposedSteps",
    "EntityResult",
    "Evidence",
    "EvidenceType",
    "FixSuggestions",
    # Layer 9: Infrastructure
    "HealthSnapshot",
    "IntentResult",
    "InventoryResult",
    "InvoiceResult",
    # Layer 1: Understanding
    "LanguageResult",
    # Layer 2: Memory & Context
    "MemoryEntries",
    "NameResult",
    "NotificationResult",
    "PipelineResult",
    "PrefetchResult",
    # Layer 7: Reasoning
    "ProblemType",
    "ReasoningResult",
    "ReasoningStep",
    "ReportResult",
    "RiskResult",
    "RoutedOperation",
    "ScaffoldResult",
    "ScheduleSpec",
    "ScoredEntries",
    "ScoredEntry",
    "SecurityResult",
    "SyntaxResult",
    "TargetResult",
    "TaskResult",
    # Layer 10: Transport
    "TextChannelInput",
    "TextChannelResult",
    "TriggerSpec",
    # Layer 5: Validation
    "ValidationIssue",
    # Layer 8: Verdict
    "Verdict",
    "VerdictInput",
    "VerdictOutput",
    "VoiceChannelInput",
    "VoiceChannelResult",
    "WorkflowSpec",
]
