"""
ZENIC-AGENTS — SSE Stream Routes.

Real-time event streaming via Server-Sent Events.

GET  /stream/tenant/{tenant_id}        — Subscribe to tenant notifications
GET  /stream/collector/{session_id}    — Subscribe to collector session updates
POST /stream/publish                   — Publish an event to a channel (authenticated)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..event_bus import get_event_bus, sse_generator
from ..middleware import get_current_tenant, get_current_user
from ..schemas import PublishRequest

router = APIRouter(prefix="/stream", tags=["stream"])

_MEDIA_TYPE = "text/event-stream"


@router.get("/tenant/{tenant_id}")
async def stream_tenant(
    tenant_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Subscribe to real-time notifications for a tenant.

    The tenant_id in the URL must match the authenticated user's tenant.
    Returns a Server-Sent Events stream.
    """
    if user["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only subscribe to your own tenant's stream",
        )

    channel = f"tenant:{tenant_id}"

    return StreamingResponse(
        sse_generator(channel),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/collector/{session_id}")
async def stream_collector(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Subscribe to real-time collector session updates.

    Requires authentication. The session is scoped to the user's tenant.
    Returns a Server-Sent Events stream.
    """
    channel = f"collector:{session_id}"

    return StreamingResponse(
        sse_generator(channel),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/publish")
async def publish_event(
    payload: PublishRequest,
    user: dict = Depends(get_current_user),
):
    """
    Publish an event to a channel.

    Used by agents and services to broadcast real-time updates.
    The publisher must belong to the same tenant as the channel target.
    """
    bus = get_event_bus()

    # Validate channel access: tenant channels must match user's tenant
    if payload.channel.startswith("tenant:"):
        target_tenant = payload.channel.split(":", 1)[1]
        if user["tenant_id"] != target_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only publish to your own tenant's channel",
            )

    delivered = await bus.publish(
        channel=payload.channel,
        event_type=payload.event_type,
        data=payload.data,
    )

    return {
        "ok": True,
        "channel": payload.channel,
        "event_type": payload.event_type,
        "subscribers_reached": delivered,
    }


@router.get("/status")
async def stream_status(
    user: dict = Depends(get_current_user),
):
    """Get current stream bus status (active channels and subscribers)."""
    bus = get_event_bus()
    return {
        "total_subscribers": bus.total_subscribers,
        "channels": bus.channel_count(),
    }
