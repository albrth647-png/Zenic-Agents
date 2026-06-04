"""
ZENIC-AGENTS — Channel Routes.

GET  /channels/available       → Listar todos los canales disponibles
GET  /channels/templates       → Listar templates disponibles
GET  /channels/prefs           → Obtener preferencias de canal del tenant
PUT  /channels/prefs           → Actualizar preferencias de canal del tenant
POST /channels/send            → Enviar notificación por el canal del tenant
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..channels import UnifiedChannel, get_channel_manager
from ..middleware import get_current_tenant, get_current_user
from ..schemas import (
    ChannelPrefsResponse,
    ChannelPrefsUpdate,
    ChannelSendRequest,
    ChannelSendResponse,
)

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/available")
def list_channels():
    """Listar todos los canales disponibles y sus prioridades."""
    from ..channels import CHANNEL_PRIORITY

    channels = []
    for ch in UnifiedChannel:
        if ch == UnifiedChannel.NONE:
            continue
        channels.append({
            "slug": ch.value,
            "name": ch.value.capitalize(),
            "priority": CHANNEL_PRIORITY.get(ch, 99),
        })
    return sorted(channels, key=lambda c: c["priority"])


@router.get("/templates")
def list_templates():
    """Listar los templates disponibles y sus keys."""
    from ..channels import DEFAULT_TEMPLATES

    result = []
    for lang, templates in DEFAULT_TEMPLATES.items():
        for key, text in templates.items():
            result.append({
                "language": lang,
                "key": key,
                "preview": text[:80] + "...",
            })
    return result


@router.get("/prefs", response_model=ChannelPrefsResponse)
def get_channel_prefs(
    tenant: dict = Depends(get_current_tenant),
    manager=Depends(get_channel_manager),
) -> ChannelPrefsResponse:
    """Obtener las preferencias de canal del tenant autenticado."""
    channel, recipient = manager.get_tenant_channel(tenant["id"])

    prefs = tenant.get("channel_prefs", {})
    return ChannelPrefsResponse(
        preferred_channel=channel.value,
        recipient=recipient,
        additional_channels=prefs.get("additional_channels", []),
    )


@router.put("/prefs", response_model=ChannelPrefsResponse)
def update_channel_prefs(
    payload: ChannelPrefsUpdate,
    tenant: dict = Depends(get_current_tenant),
    manager=Depends(get_channel_manager),
) -> ChannelPrefsResponse:
    """Actualizar las preferencias de canal del tenant autenticado."""
    result = manager.set_tenant_channel(
        tenant_id=tenant["id"],
        preferred_channel=payload.preferred_channel,
        recipient=payload.recipient or "",
        additional_channels=payload.additional_channels,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {payload.preferred_channel}. "
                   f"Choose from: {[c.value for c in UnifiedChannel]}",
        )

    return ChannelPrefsResponse(
        preferred_channel=payload.preferred_channel,
        recipient=payload.recipient or "",
        additional_channels=payload.additional_channels or [],
    )


@router.post("/send", response_model=ChannelSendResponse)
def send_notification(
    payload: ChannelSendRequest,
    tenant: dict = Depends(get_current_tenant),
    manager=Depends(get_channel_manager),
) -> ChannelSendResponse:
    """
    Enviar una notificación al tenant por su canal preferido.

    El tenant autenticado solo puede enviar a sí mismo.
    El admin puede enviar a cualquier tenant.
    """
    target_tenant_id = payload.tenant_id or tenant["id"]

    if target_tenant_id != tenant["id"] and tenant.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo admins pueden enviar a otros tenants",
        )

    result = manager.send(
        tenant_id=target_tenant_id,
        message=payload.message,
        template_key=payload.template_key or "notification",
        niche_id=payload.niche_id or "default",
        channel_override=payload.channel_override or None,
        template_vars=payload.template_vars or None,
    )

    return ChannelSendResponse(
        success=result["success"],
        channel=result["channel"],
        recipient=result.get("recipient", ""),
        message=result.get("message", payload.message),
        sent_via=result.get("sent_via", "none"),
        language=result.get("language", "es"),
    )
