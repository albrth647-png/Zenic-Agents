"""
ZENIC-AGENTS — Schema stubs (standalone mode).

Minimal dataclass definitions for all schema types used by _archived agents.
When the full src/ tree is available, these are replaced by the real schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


# ── Enums ──────────────────────────────────────────────────────

class Verdict(str, Enum):
    YES = "YES"
    NO = "NO"


class EvidenceType(IntEnum):
    SECURITY_CHECK = 1
    SYNTAX_VALIDATION = 2
    KEYWORD_CLASSIFY = 3
    PATTERN_MATCH = 4
    ENTITY_EXTRACT = 5
    INTENT_CLASSIFY = 6
    MEMORY_LOOKUP = 7
    CONSENSUS = 8
    USER_FEEDBACK = 9
    AUDIT_TRAIL = 10
    SANDBOX_PASS = 11
    SANDBOX_FAIL = 12
    CRITICALITY = 13
    CODE_EXECUTION = 14
    SYNTAX_VALID = 15
    AST_VALIDATION = 16
    CACHE_HIT = 17
    TYPE_SAFETY = 18
    RULE_ENGINE = 19
    STRUCTURAL_MATCH = 20
    REGEX_MATCH = 21
    SEMANTIC_SIMILARITY = 22


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class Language(str, Enum):
    ES = "es"
    EN = "en"


# ── Evidence / Verdict schemas ─────────────────────────────────

@dataclass
class Evidence:
    type: EvidenceType = EvidenceType.KEYWORD_CLASSIFY
    detail: str = ""
    weight: float = 1.0
    favors: Verdict = Verdict.NO
    source: str = "deterministic"


@dataclass
class VerdictInput:
    question: str = ""
    evidence_for: list[Evidence] = field(default_factory=list)
    evidence_against: list[Evidence] = field(default_factory=list)
    consensus_result: ConsensusResult | None = None


@dataclass
class VerdictOutput:
    verdict: Verdict = Verdict.NO
    confidence: float = 0.1
    source: str = "fallback"
    evidence_summary: str = ""
    llm_used: bool = False
    llm_raw_response: str = ""
    retry_count: int = 0
    duration_ms: float = 0.0


@dataclass
class ConsensusResult:
    verdict: Verdict = Verdict.NO
    confidence: float = 0.5
    needs_llm: bool = False
    evidence_count: int = 0
    vetos: list[str] = field(default_factory=list)


# ── Understanding schemas ──────────────────────────────────────

@dataclass
class IntentResult:
    intent: str = ""
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class EntityResult:
    entities: list[dict[str, Any]] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class TargetResult:
    target: str = ""
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass
class LanguageResult:
    language: str = "unknown"
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass
class CriticalityResult:
    level: int = 0
    confidence: float = 0.5
    reason: str = ""
    source: str = "deterministic"


# ── Reasoning schemas ──────────────────────────────────────────

@dataclass
class ProblemType:
    type: str = "unknown"
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass
class ReasoningStep:
    step: str = ""
    result: str = ""
    confidence: float = 0.5


@dataclass
class ReasoningResult:
    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass
class DecomposedSteps:
    steps: list[ReasoningStep] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class Conclusion:
    text: str = ""
    confidence: float = 0.5
    source: str = "deterministic"


@dataclass
class ConfidenceResult:
    score: float = 0.5
    source: str = "deterministic"


# ── Memory schemas ─────────────────────────────────────────────

@dataclass
class ScoredEntry:
    key: str = ""
    content: str = ""
    score: float = 0.0
    memory_type: str = "WORKING"


@dataclass
class ScoredEntries:
    entries: list[ScoredEntry] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class MemoryEntries:
    entries: list[ScoredEntry] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class CompressedContext:
    compressed: str = ""
    original_tokens: int = 0
    compressed_tokens: int = 0
    source: str = "deterministic"


@dataclass
class PrefetchResult:
    prefetched: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


# ── Validation schemas ─────────────────────────────────────────

@dataclass
class ValidationIssue:
    code: str = ""
    message: str = ""
    severity: str = "WARNING"
    line: int = 0
    suggestion: str = ""


@dataclass
class SyntaxResult:
    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class SecurityResult:
    safe: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class RiskResult:
    risk_level: str = "LOW"
    score: float = 0.0
    issues: list[ValidationIssue] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class FixSuggestions:
    suggestions: list[dict[str, str]] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class ChainResult:
    valid: bool = True
    blocks: list[Any] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class ConfigResult:
    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    defaults_applied: list[str] = field(default_factory=list)
    source: str = "deterministic"


# ── Infrastructure schemas ─────────────────────────────────────

@dataclass
class AgentResult:
    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    source: str = "deterministic"


@dataclass
class HealthSnapshot:
    healthy: bool = True
    success_rates: dict[str, float] = field(default_factory=dict)
    latencies: dict[str, float] = field(default_factory=dict)
    circuit_breaker_states: dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = "deterministic"


# ── Business schemas ───────────────────────────────────────────

@dataclass
class InvoiceResult:
    success: bool = True
    invoice_id: str = ""
    amount: float = 0.0
    status: str = "pending"
    error: str = ""
    source: str = "deterministic"


@dataclass
class InventoryResult:
    success: bool = True
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    source: str = "deterministic"


@dataclass
class AnalyticsResult:
    success: bool = True
    metrics: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


@dataclass
class CRMResult:
    stages: list[dict[str, Any]] = field(default_factory=list)
    conversions: dict[str, Any] = field(default_factory=dict)
    forecasts: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


@dataclass
class TaskResult:
    success: bool = True
    task_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


@dataclass
class ReportResult:
    success: bool = True
    report: str = ""
    format: str = "text"
    source: str = "deterministic"


@dataclass
class NotificationResult:
    success: bool = True
    sent: bool = False
    channel: str = ""
    error: str = ""
    source: str = "deterministic"


@dataclass
class RoutedOperation:
    success: bool = True
    operation: str = ""
    target: str = ""
    source: str = "deterministic"


# ── Automation schemas ─────────────────────────────────────────

@dataclass
class AutoDescription:
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerSpec:
    type: str = "schedule"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionSpec:
    type: str = "notification"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleSpec:
    type: str = "daily"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowSpec:
    name: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    source: str = "deterministic"


@dataclass
class ConditionResult:
    condition: str = ""
    logic_tree: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


@dataclass
class NameResult:
    name: str = "automation"
    slug: str = "automation"
    source: str = "deterministic"


# ── Pipeline schemas ───────────────────────────────────────────

@dataclass
class CodeResult:
    """Result from code execution in sandbox."""
    success: bool = True
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0


@dataclass
class PipelineResult:
    status: str = "ok"
    results: dict[str, Any] = field(default_factory=dict)
    source: str = "deterministic"


# ── Interactive Data Collector schemas ─────────────────────────

@dataclass
class InteractiveCollectionResult:
    session_id: str = ""
    niche_id: str = ""
    questions: list[dict[str, Any]] = field(default_factory=list)
    answers_applied: int = 0
    answers_rejected: int = 0
    still_missing: int = 0
    completion_pct: float = 0.0
    is_complete: bool = False
    round_number: int = 0
    source: str = "deterministic"
