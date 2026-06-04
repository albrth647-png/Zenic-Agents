"""
ZENIC-AGENTS — API Pydantic Schemas.

Request/response models for the REST API.
All models use strict validation and friendly defaults.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# CLIENT SCHEMAS
# ──────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    """Payload for creating a new client."""
    name: str = Field(..., min_length=1, max_length=200, description="Client name")
    email: str = Field(default="", max_length=200, description="Client email")
    company: str = Field(default="", max_length=200, description="Company name")
    phone: str = Field(default="", max_length=50, description="Phone number")
    stage: str = Field(default="new", description="Pipeline stage")


class ClientUpdate(BaseModel):
    """Payload for updating an existing client (all fields optional)."""
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    stage: str | None = Field(default=None)


class ClientResponse(BaseModel):
    """Single client as returned by the API."""
    id: int
    tenant_id: str = ""
    name: str
    email: str = ""
    company: str = ""
    phone: str = ""
    stage: str = "new"
    created_at: str = ""


class ClientListResponse(BaseModel):
    """List of clients with metadata."""
    clients: list[ClientResponse]
    total: int


class StatsResponse(BaseModel):
    """CRM statistics."""
    total_clients: int
    by_stage: dict[str, int]


class PipelineResponse(BaseModel):
    """Pipeline view: clients grouped by stage."""
    stages: dict[str, list[ClientResponse]]


# ──────────────────────────────────────────────────────────────
# COLLECTOR SCHEMAS
# ──────────────────────────────────────────────────────────────

class CollectorStartRequest(BaseModel):
    """Start a new interactive collection session."""
    niche_id: str = Field(default="default", min_length=1, max_length=100)


class CollectorQuestionsRequest(BaseModel):
    """Request questions for a session (body model)."""
    session_id: str = Field(..., min_length=1)
    template_dict: dict[str, Any] = Field(default_factory=dict)


class CollectorFinalizeRequest(BaseModel):
    """Finalize a collection session (body model)."""
    session_id: str = Field(..., min_length=1)
    template_dict: dict[str, Any] = Field(default_factory=dict)


class CollectorAnswerRequest(BaseModel):
    """Submit a single answer."""
    session_id: str = Field(..., min_length=1)
    template_dict: dict[str, Any] = Field(default_factory=dict)
    field_name: str = Field(..., min_length=1)
    value: str = Field(default="")
    field_type: str = Field(default="text")


class CollectorBatchAnswerRequest(BaseModel):
    """Submit multiple answers at once."""
    session_id: str = Field(..., min_length=1)
    template_dict: dict[str, Any] = Field(default_factory=dict)
    answers: dict[str, str] = Field(default_factory=dict)


class CollectorValidateRequest(BaseModel):
    """Validate an answer without submitting."""
    field_type: str = Field(default="text")
    value: str = Field(default="")
    enum_variants: list[str] = Field(default_factory=list)


class CollectorSessionResponse(BaseModel):
    """Response from any collector operation."""
    session_id: str = ""
    niche_id: str = ""
    questions: list[dict[str, Any]] = Field(default_factory=list)
    answers_applied: int = 0
    answers_rejected: int = 0
    still_missing: int = 0
    completion_pct: float = 0.0
    is_complete: bool = False
    round_number: int = 0
    source: str = "deterministic"


class CollectorSuggestionsRequest(BaseModel):
    """Request field suggestions."""
    field_name: str = Field(..., min_length=1)
    field_type: str = Field(default="text")


# ──────────────────────────────────────────────────────────────
# ADMIN SCHEMAS
# ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """System health status."""
    healthy: bool = True
    success_rates: dict[str, float] = Field(default_factory=dict)
    latencies: dict[str, float] = Field(default_factory=dict)
    circuit_breaker_states: dict[str, str] = Field(default_factory=dict)
    timestamp: float = 0.0
    source: str = "deterministic"


class AuditEntryResponse(BaseModel):
    """Single audit log entry."""
    agent: str = ""
    input_hash: str = ""
    output_hash: str = ""
    source: str = "deterministic"
    confidence: float = 0.0
    duration_ms: float = 0.0
    retry_count: int = 0
    circuit_breaker_state: str = "CLOSED"
    evidence_summary: str = ""
    timestamp: float = 0.0


class AuditListResponse(BaseModel):
    """List of audit entries."""
    entries: list[AuditEntryResponse]
    total: int


class ConfigResponse(BaseModel):
    """Current agent configuration (safe, no secrets)."""
    host: str
    port: int
    log_level: str
    max_sessions: int
    rate_limit_rpm: int
    personality: str
    language: str
    streaming_enabled: bool
    tools_enabled: bool
    memory_enabled: bool
    debug: bool


# ──────────────────────────────────────────────────────────────
# AUTH SCHEMAS
# ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Registration payload."""
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(default="", max_length=200)
    role: str = Field(default="agent")
    tenant_id: str = Field(default="")


class LoginRequest(BaseModel):
    """Login payload."""
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)


class UserResponse(BaseModel):
    """Public user info (no password)."""
    id: str
    tenant_id: str
    email: str
    role: str = "agent"
    name: str = ""
    created_at: str = ""


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ──────────────────────────────────────────────────────────────
# PLAN / SUBSCRIPTION SCHEMAS
# ──────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    """Subscription plan details."""
    slug: str
    name: str
    max_clients: int
    max_messages_per_day: int
    max_collector_sessions: int
    features: list[str]


class UsageResponse(BaseModel):
    """Current usage for a tenant."""
    plan: str
    plan_name: str
    daily: dict = {}
    total_clients: int = 0
    total_clients_limit: int = 0
    features: list[str] = []


class UpgradeRequest(BaseModel):
    """Payload to upgrade a tenant's plan."""
    tenant_id: str = Field(..., min_length=1)
    plan: str = Field(..., min_length=1)


# ──────────────────────────────────────────────────────────────
# SSE / STREAM SCHEMAS
# ──────────────────────────────────────────────────────────────

class PublishRequest(BaseModel):
    """Payload to publish an event to a stream channel."""
    channel: str = Field(..., min_length=1, description="e.g. tenant:abc, collector:sess_123")
    event_type: str = Field(..., min_length=1, description="notification, collector, system, etc.")
    data: dict = Field(default_factory=dict, description="Event payload (arbitrary JSON)")


# ──────────────────────────────────────────────────────────────
# CHANNEL / NOTIFICATION SCHEMAS
# ──────────────────────────────────────────────────────────────

class ChannelPrefsResponse(BaseModel):
    """Channel preferences for a tenant."""
    preferred_channel: str = "web"
    recipient: str = ""
    additional_channels: list[str] = []


class ChannelPrefsUpdate(BaseModel):
    """Payload to update channel preferences."""
    preferred_channel: str = Field(..., min_length=1, max_length=30)
    recipient: str = Field(default="", max_length=200)
    additional_channels: list[str] = Field(default_factory=list)


class ChannelSendRequest(BaseModel):
    """Payload to send a notification."""
    message: str = Field(default="", max_length=10000, description="Message text (can be empty if template_vars provided)")
    tenant_id: str = Field(default="", description="Target tenant (admin only)")
    channel_override: str = Field(default="", description="Force specific channel")
    template_key: str = Field(default="notification", description="notification, alert, confirmation, error")
    niche_id: str = Field(default="default", description="Niche for template selection")
    template_vars: dict = Field(default_factory=dict, description="Variables to render in template")


class ChannelSendResponse(BaseModel):
    """Result of sending a notification."""
    success: bool
    channel: str = ""
    recipient: str = ""
    message: str = ""
    sent_via: str = ""
    language: str = "es"
