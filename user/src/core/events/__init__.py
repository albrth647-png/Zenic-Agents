"""
ZENIC-AGENTS — Event-driven Actions Engine (B1)

Package providing the core event-driven automation components:

  - TriggerMap: Declarative mapping from event patterns to automations
  - EventSchemaRegistry: Event payload validation against declared schemas
  - ReplayQueue: Dead-letter queue with event replay capability

Removed (external API connections deleted):
  - WebhookIngestionEngine: Was inbound webhook handler with HMAC verification

Each component is thread-safe and follows the singleton pattern
for production use. All SQLite-persisted components store data
under ~/.zenic_agents/db/ by default.
"""

# ── TriggerMap ──
# ── ReplayQueue ──
from .replay_queue import (
    BatchRetryResult,
    DeadLetterEvent,
    DeadLetterStatus,
    ReplayQueue,
    RetryResult,
    get_replay_queue,
    reset_replay_queue,
)

# ── EventSchemaRegistry ──
from .schema_registry import (
    EventSchema,
    EventSchemaRegistry,
    IssueType,
    ValidationIssue,
    ValidationResult,
    get_schema_registry,
    reset_schema_registry,
)
from .trigger_map import (
    ConditionOperator,
    TriggerCondition,
    TriggerMap,
    TriggerMapping,
    get_trigger_map,
    reset_trigger_map,
)

__all__ = [
    "BatchRetryResult",
    "ConditionOperator",
    "DeadLetterEvent",
    "DeadLetterStatus",
    "EventSchema",
    # EventSchemaRegistry
    "EventSchemaRegistry",
    "IssueType",
    # ReplayQueue
    "ReplayQueue",
    "RetryResult",
    "TriggerCondition",
    # TriggerMap
    "TriggerMap",
    "TriggerMapping",
    "ValidationIssue",
    "ValidationResult",
    "get_replay_queue",
    "get_schema_registry",
    "get_trigger_map",
    "reset_replay_queue",
    "reset_schema_registry",
    "reset_trigger_map",
]
