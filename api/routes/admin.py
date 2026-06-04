"""
ZENIC-AGENTS — Admin Routes.

Health monitoring, audit logs, and configuration endpoints.
Protected: require authentication. Admin-only routes require admin role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_health_monitor, get_audit_logger, get_app_config
from ..middleware import get_current_user, require_admin
from ..schemas import (
    HealthResponse,
    AuditEntryResponse,
    AuditListResponse,
    ConfigResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── HEALTH ────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
def system_health(
    user: dict = Depends(get_current_user),
    monitor=Depends(get_health_monitor),
) -> HealthResponse:
    """Get system-wide health snapshot (authenticated)."""
    snap = monitor.execute("all")
    return _health_to_response(snap)


@router.get("/health/unhealthy", response_model=HealthResponse)
def unhealthy_agents(
    user: dict = Depends(get_current_user),
    monitor=Depends(get_health_monitor),
) -> HealthResponse:
    """Get health snapshot of only unhealthy/warning agents."""
    snap = monitor.execute({"action": "unhealthy"})
    return _health_to_response(snap)


@router.get("/health/{agent_name}", response_model=HealthResponse)
def agent_health(
    agent_name: str,
    user: dict = Depends(get_current_user),
    monitor=Depends(get_health_monitor),
) -> HealthResponse:
    """Get health snapshot for a specific agent."""
    snap = monitor.execute({"action": "agent", "agent_name": agent_name})
    return _health_to_response(snap)


# ── AUDIT ─────────────────────────────────────────────────────

@router.get("/audit", response_model=AuditListResponse)
def list_audit(
    agent_name: str | None = None,
    count: int = 20,
    admin: dict = Depends(require_admin),
    logger=Depends(get_audit_logger),
) -> AuditListResponse:
    """List recent audit log entries (admin only)."""
    result = logger.execute({
        "action": "query",
        "agent_name": agent_name,
        "count": count,
    })
    entries_data = []
    if hasattr(result, "data"):
        entries_data = result.data if isinstance(result.data, list) else []
    elif isinstance(result, dict):
        entries_data = result.get("data", [])

    entries = [
        AuditEntryResponse(
            agent=e.get("agent", e.get("agent_name", "")),
            input_hash=e.get("input_hash", ""),
            output_hash=e.get("output_hash", ""),
            source=e.get("source", "deterministic"),
            confidence=e.get("confidence", 0.0),
            duration_ms=e.get("duration_ms", 0.0),
            retry_count=e.get("retry_count", 0),
            circuit_breaker_state=e.get("circuit_breaker_state", "CLOSED"),
            evidence_summary=e.get("evidence_summary", ""),
            timestamp=e.get("timestamp", 0.0),
        )
        for e in entries_data
    ]
    return AuditListResponse(entries=entries, total=len(entries))


# ── CONFIG ────────────────────────────────────────────────────

@router.get("/config", response_model=ConfigResponse)
def app_config(
    admin: dict = Depends(require_admin),
    config=Depends(get_app_config),
) -> ConfigResponse:
    """Get current agent configuration (admin only, no secrets)."""
    d = config.to_dict()
    return ConfigResponse(
        host=str(d.get("host", "")),
        port=int(d.get("port", 0)),
        log_level=str(d.get("log_level", "")),
        max_sessions=int(d.get("max_sessions", 0)),
        rate_limit_rpm=int(d.get("rate_limit_rpm", 0)),
        personality=str(d.get("personality", "")),
        language=str(d.get("language", "")),
        streaming_enabled=bool(d.get("streaming_enabled", False)),
        tools_enabled=bool(d.get("tools_enabled", False)),
        memory_enabled=bool(d.get("memory_enabled", False)),
        debug=bool(d.get("debug", False)),
    )


# ── Helpers ───────────────────────────────────────────────────

def _health_to_response(snap) -> HealthResponse:
    """Convert a HealthSnapshot to the API response model."""
    if hasattr(snap, "__dict__"):
        d = {k: v for k, v in snap.__dict__.items() if not k.startswith("_")}
    elif isinstance(snap, dict):
        d = snap
    else:
        d = {}

    return HealthResponse(
        healthy=d.get("healthy", True),
        success_rates=d.get("success_rates", {}),
        latencies=d.get("latencies", {}),
        circuit_breaker_states=d.get("circuit_breaker_states", {}),
        timestamp=d.get("timestamp", 0.0),
        source=d.get("source", "deterministic"),
    )
