from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryTier(str, Enum):
    EPHEMERAL = "ephemeral"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    PERMANENT = "permanent"


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    FACT = "fact"
    PROCEDURE = "procedure"
    PREFERENCE = "preference"
    CONTEXT = "context"
    EMOTION = "emotion"


@dataclass
class MemoryRecord:
    id: str = ""
    tier: MemoryTier = MemoryTier.SHORT_TERM
    mem_type: MemoryType = MemoryType.CONVERSATION
    content: str = ""
    session_id: str = ""
    user_id: int | None = None
    importance: float = 0.5
    access_count: int = 0
    decay_factor: float = 1.0
    created_at: str = ""
    last_accessed: str = ""
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding_hash: str = ""


@dataclass
class MemoryQuery:
    query_text: str = ""
    tiers: set[MemoryTier] = field(default_factory=set)
    types: set[MemoryType] = field(default_factory=set)
    session_id: str | None = None
    min_importance: float = 0.0
    max_results: int = 20


@dataclass
class MemorySearchResult:
    records: list[MemoryRecord] = field(default_factory=list)
    total: int = 0
    best_score: float = 0.0


@dataclass
class ContextWindow:
    id: str = ""
    session_id: str = ""
    records: list[MemoryRecord] = field(default_factory=list)
    token_count: int = 0
    max_tokens: int = 4096
    summary: str = ""
    created_at: str = ""
