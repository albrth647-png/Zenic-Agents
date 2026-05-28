"""
Tipos compartidos del Asistente (Fase 2).

Single source of truth para todas las dataclasses, enums,
protocols y tipos del modulo zenic_agents.conversational.

Fase 1: session, intent, response, personality, tool_use, base, memory, events
Fase 2: conversation state, knowledge types (added to existing)
"""

from .base import (
    Classifier,
    Emitter,
    Err,
    Generator,
    Ok,
    PipelineContext,
    Priority,
    Processor,
    Result,
    Router,
    Severity,
    Store,
    err,
    new_id,
    ok,
)
from .events import (
    AsyncEventHandler,
    Event,
    EventHandler,
    EventType,
    Subscription,
)
from .intent import (
    AssistantIntent,
    ConversationMode,
    IntentCategory,
    IntentResult,
)
from .memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
)
from .personality import (
    LanguagePreference,
    PersonalityProfile,
    ToneLevel,
)
from .response import (
    AssistantResponse,
    ResponseFormat,
    ResponseMetadata,
    StreamingChunk,
)
from .session import (
    Message,
    MessageMetadata,
    MessageRole,
    Session,
    SessionConfig,
    SessionId,
    SessionState,
)
from .tool_use import (
    ToolCall,
    ToolPermission,
    ToolResult,
    ToolSpec,
)

__all__ = [
    # Intent
    "AssistantIntent",
    # Response
    "AssistantResponse",
    "AsyncEventHandler",
    "Classifier",
    "ConversationMode",
    "Emitter",
    "Err",
    # Events (Fase 1)
    "Event",
    "EventHandler",
    "EventType",
    "Generator",
    "IntentCategory",
    "IntentResult",
    "LanguagePreference",
    "MemoryCategory",
    # Memory (Fase 1)
    "MemoryEntry",
    "MemoryQuery",
    "MemoryResult",
    "MemoryStats",
    "MemoryType",
    "Message",
    "MessageMetadata",
    "MessageRole",
    "Ok",
    # Personality
    "PersonalityProfile",
    "PipelineContext",
    "Priority",
    "Processor",
    "ResponseFormat",
    "ResponseMetadata",
    # Base (Fase 1)
    "Result",
    "Router",
    "Session",
    "SessionConfig",
    # Session
    "SessionId",
    "SessionState",
    "Severity",
    "Store",
    "StreamingChunk",
    "Subscription",
    "ToneLevel",
    # Tool Use
    "ToolCall",
    "ToolPermission",
    "ToolResult",
    "ToolSpec",
    "err",
    "new_id",
    "ok",
]
