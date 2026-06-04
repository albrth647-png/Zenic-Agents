"""
ZENIC-AGENTS — Shared Memory Bus: Types, Constants, and Data Classes.

This module defines the core enumerations, data classes, and constants
used throughout the shared memory bus subsystem.
"""

import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RING_SLOT_SIZE: int = 4096  # 4 KB per slot
_DEFAULT_RING_SIZE: int = 1024  # 1024 slots → 4 MB
_MAX_MAILBOX_DEPTH: int = 100
_FLUSH_INTERVAL_S: float = 0.05  # 50 ms
_FLUSH_BATCH_SIZE: int = 100
_DB_CACHE_SIZE: int = -8192  # 8 MB
_DB_MMAP_SIZE: int = 67108864  # 64 MB

# Struct format for ring-buffer slot header:
#   4 bytes data_length (uint32)  |  4 bytes tenant_hash (uint32)
#   = 8-byte header per slot
_SLOT_HEADER_FMT = "<II"
_SLOT_HEADER_SIZE = struct.calcsize(_SLOT_HEADER_FMT)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MessageType(IntEnum):
    """Message type classification for agent communication."""

    DATA = 0
    CONTROL = 1
    ERROR = 2


class Priority(IntEnum):
    """Priority levels for mailbox message ordering.

    Lower numeric value = higher priority (retrieved first).
    """

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BusMessage:
    """A single message travelling through the shared memory bus.

    Attributes:
        sender: Agent ID of the sender (e.g., "A01").
        recipient: Agent ID of the recipient, or "broadcast".
        msg_type: Classification of the message.
        priority: Ordering priority (lower = higher priority).
        payload: The actual data carried by the message.
        timestamp: Monotonic timestamp when the message was created.
        tenant_id: Tenant isolation identifier.
        ttl_seconds: Time-to-live in seconds (0 = no expiry).
        correlation_id: Optional ID for request-response correlation.
    """

    sender: str
    recipient: str
    msg_type: MessageType
    priority: Priority
    payload: Any
    timestamp: float = field(default_factory=time.monotonic)
    tenant_id: str = "default"
    ttl_seconds: float = 300.0
    correlation_id: str = ""


# ---------------------------------------------------------------------------
# Knowledge Graph Types (for cross_agent.py)
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeNode:
    """A node in the cross-agent knowledge graph.

    Attributes:
        id: Unique node identifier.
        domain: Knowledge domain (e.g., "business", "validation").
        concept: Concept name.
        content: Text content of the node.
        tags: Set of tags for categorization.
        confidence: Confidence score (0.0–1.0).
        source: Source agent or system.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        access_count: Number of times this node was accessed.
    """

    id: str
    domain: str
    concept: str
    content: str
    tags: set[str] = field(default_factory=set)
    confidence: float = 0.5
    source: str = ""
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0


@dataclass
class KnowledgeEdge:
    """An edge connecting two nodes in the knowledge graph.

    Attributes:
        id: Unique edge identifier.
        source_id: ID of the source node.
        target_id: ID of the target node.
        relation_type: Type of relationship (e.g., "propagated_to").
        weight: Edge weight (0.0–1.0).
        created_at: ISO timestamp of creation.
    """

    id: str
    source_id: str
    target_id: str
    relation_type: str = "related_to"
    weight: float = 1.0
    created_at: str = ""
