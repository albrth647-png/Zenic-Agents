"""_compat_bridge — Puente de compatibilidad entre legacy core/channel/ y nuevo core/channels/

Traduce tipos y llamadas del sistema legacy (TextMessage, TextResult, ChannelType)
al nuevo sistema (ChannelMessage, ChannelResponse, AdapterRegistry) para que
el código legacy pueda usar los providers reales sin cambios.

Estrategia de migración:
  1. El _compat_bridge se inyecta en ProactiveChannelBridge y MessageBridge
  2. Si hay providers registrados en AdapterRegistry, usa el nuevo sistema
  3. Si no, cae al legacy TextChannelAgent (backward compatible)
  4. Una vez migrado todo, se elimina el código legacy

Design invariants:
  1. Nunca rompe la API pública del sistema legacy
  2. Siempre retorna tipos compatibles (TextResult o similar)
  3. El AdapterRegistry singleton se obtiene via get_default_registry()
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .a53_text import ChannelType as LegacyChannelType, TextMessage, TextResult
# ─── External imports (wrapped: may not be available in standalone mode) ───
try:
    from src.core.channels._registry import AdapterRegistry, get_default_registry
except ImportError:
    AdapterRegistry = None  # type: ignore[assignment,misc]
    get_default_registry = None  # type: ignore[assignment]

try:
    from src.core.channels._types import (
        ChannelCapability,
        ChannelMessage,
        ChannelPriority,
        ChannelResponse,
        DeliveryStatus,
    )
except ImportError:
    ChannelCapability = None  # type: ignore[assignment,misc]
    ChannelMessage = None  # type: ignore[assignment,misc]
    ChannelPriority = None  # type: ignore[assignment,misc]
    ChannelResponse = None  # type: ignore[assignment,misc]
    DeliveryStatus = None  # type: ignore[assignment,misc]

try:
    from src.core.sna.alert_manager import Alert, AlertSeverity
except ImportError:
    Alert = None  # type: ignore[assignment,misc]
    AlertSeverity = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ─── Mapeo de tipos legacy → nuevo sistema ─────────────────────

LEGACY_TO_NEW_CHANNEL: dict[str, str] = {
    LegacyChannelType.WHATSAPP.value: "whatsapp",
    LegacyChannelType.TELEGRAM.value: "telegram",
    LegacyChannelType.WEB.value: "log",
    LegacyChannelType.SMS.value: "sms",
}

NEW_CHANNEL_TO_LEGACY: dict[str, str] = {
    v: k for k, v in LEGACY_TO_NEW_CHANNEL.items()
}

# String-based fallback dicts (external enum types may be unavailable)
ALERT_SEVERITY_TO_PRIORITY: dict[str, str] = {
    "OK": "LOW",
    "INFO": "NORMAL",
    "WARNING": "HIGH",
    "CRITICAL": "URGENT",
}

LEGACY_SEVERITY_TO_PRIORITY: dict[str, str] = {
    "ok": "LOW",
    "info": "NORMAL",
    "warning": "HIGH",
    "critical": "URGENT",
}


# ─── Conversores ───────────────────────────────────────────────


def text_message_to_channel_msg(
    text_msg: TextMessage,
) -> ChannelMessage:
    """Convierte un TextMessage legacy a ChannelMessage del nuevo sistema.

    Args:
        text_msg: Mensaje de texto del sistema legacy.

    Returns:
        ChannelMessage compatible con el nuevo ChannelProvider protocol.
    """
    channel_name = LEGACY_TO_NEW_CHANNEL.get(getattr(text_msg.channel, "value", str(text_msg.channel)), "log")

    return ChannelMessage(
        text=text_msg.text,
        recipient=text_msg.recipient,
        reply_to=text_msg.metadata.get("reply_to", ""),
        metadata={
            **text_msg.metadata,
            "legacy_channel": text_msg.channel.value,
            "is_proactive": text_msg.is_proactive,
            "sender": text_msg.sender,
        },
    )


def alert_to_channel_msg(
    alert: Alert,
    channel_name: str = "",
) -> ChannelMessage:
    """Convierte una Alert del SNA a ChannelMessage.

    Args:
        alert: Alerta del AlertManager/SNA.
        channel_name: Canal destino (opcional, se infiere de alert.channel).

    Returns:
        ChannelMessage listo para enviar via AdapterRegistry.
    """
    target = channel_name or getattr(alert.channel, "value", str(alert.channel))
    priority = ChannelPriority.NORMAL
    if ChannelPriority is not None:
        priority = ALERT_SEVERITY_TO_PRIORITY.get(
            getattr(alert.severity, "value", str(alert.severity)),
            ChannelPriority.NORMAL,
        )

    return ChannelMessage(
        text=alert.message,
        recipient="",
        priority=priority,
        metadata={
            "alert_id": alert.id,
            "monitor_name": alert.monitor_name,
            "severity": alert.severity.value,
            "alert_channel": alert.channel.value,
            "findings": alert.findings,
            "details": alert.details,
            "fingerprint": alert.fingerprint,
            "source": "sna",
        },
    )


def channel_response_to_text_result(
    response: ChannelResponse,
    original: TextMessage | None = None,
) -> TextResult:
    """Convierte ChannelResponse a TextResult legacy para compatibilidad.

    Args:
        response: Respuesta del nuevo sistema.
        original: TextMessage original (opcional, para mantener referencia).

    Returns:
        TextResult compatible con el sistema legacy.
    """
    return TextResult(
        success=response.success,
        delivered=response.status in (DeliveryStatus.SENT, DeliveryStatus.DELIVERED, DeliveryStatus.FALLBACK, DeliveryStatus.DRY_RUN),
        sanitized_text=original.text if original else "",
        chunks_sent=1 if response.success else 0,
        fallback_used=response.status == DeliveryStatus.FALLBACK,
        fallback_channel=(
            NEW_CHANNEL_TO_LEGACY.get(response.channel)
            if response.status == DeliveryStatus.FALLBACK
            else None
        ),
        error=response.error,
        original=original,
    )


# ─── Bridge de envío ───────────────────────────────────────────


class CompatibilityBridge:
    """Puente que permite al código legacy usar el nuevo AdapterRegistry.

    Se inyecta en ProactiveChannelBridge y ChannelBootstrap para
    que usen providers reales (Telegram, WhatsApp) en vez de
    TextChannelAgent simulado.

    Uso:
        bridge = CompatibilityBridge(registry=get_default_registry())
        result = bridge.send_proactive(alert)
        result = bridge.send_text(text_message)
    """

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
    ) -> None:
        self._registry = registry or get_default_registry()
        self._sent_count: int = 0
        self._failed_count: int = 0

        logger.info(
            "CompatibilityBridge: inicializado (providers=%s)",
            self._registry.registered_channels,
        )

    # ── Envío de alertas SNA ────────────────────────────────────

    def send_alert(
        self,
        alert: Alert,
        channel_name: str = "",
    ) -> TextResult:
        """Envía una alerta SNA usando el nuevo AdapterRegistry.

        Args:
            alert: Alerta del AlertManager.
            channel_name: Canal destino (opcional).

        Returns:
            TextResult con resultado del envío.
        """
        target = channel_name or alert.channel.value
        msg = alert_to_channel_msg(alert, target)

        logger.info(
            "CompatBridge: enviando alerta [%s] %s → %s",
            alert.severity.value,
            alert.monitor_name,
            target,
        )

        response = self._send(msg, target)
        return channel_response_to_text_result(response)

    # ── Envío de mensajes de texto legacy ───────────────────────

    def send_text(
        self,
        text_msg: TextMessage,
    ) -> TextResult:
        """Envía un TextMessage legacy usando el nuevo sistema.

        Args:
            text_msg: Mensaje de texto legacy.

        Returns:
            TextResult con resultado del envío.
        """
        channel_name = LEGACY_TO_NEW_CHANNEL.get(getattr(text_msg.channel, "value", str(text_msg.channel)), "log")
        msg = text_message_to_channel_msg(text_msg)

        logger.info(
            "CompatBridge: enviando texto legacy → %s (proactive=%s)",
            channel_name,
            text_msg.is_proactive,
        )

        response = self._send(msg, channel_name)
        return channel_response_to_text_result(response, text_msg)

    # ── Envío a provider específico ─────────────────────────────

    def send_to_channel(
        self,
        channel_name: str,
        msg: ChannelMessage,
    ) -> ChannelResponse:
        """Envía un ChannelMessage directamente a un provider.

        Args:
            channel_name: Nombre del provider (telegram, whatsapp, etc.).
            msg: Mensaje en formato nuevo.

        Returns:
            ChannelResponse del provider.
        """
        return self._send(msg, channel_name)

    # ── Interno ─────────────────────────────────────────────────

    def _send(
        self,
        msg: ChannelMessage,
        channel_name: str,
    ) -> ChannelResponse:
        """Envía un mensaje con fallback al canal especificado.

        Si el canal primario no está disponible, intenta la cadena
        de fallback configurada en el AdapterRegistry.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Ya hay un event loop — crear y ejecutar coro
            import asyncio as _asyncio

            try:
                response = _asyncio.run_coroutine_threadsafe(
                    self._registry.send_with_fallback(channel_name, msg),
                    loop,
                ).result(timeout=30)
            except Exception as e:
                logger.error("CompatBridge: error en async send: %s", e)
                self._failed_count += 1
                return ChannelResponse(
                    success=False,
                    channel=channel_name,
                    status=DeliveryStatus.FAILED,
                    error=f"Async send failed: {e}",
                    timestamp=time.time(),
                )
        else:
            # No hay event loop — crear uno nuevo
            import asyncio as _asyncio

            try:
                response = _asyncio.run(
                    self._registry.send_with_fallback(channel_name, msg),
                )
            except Exception as e:
                logger.error("CompatBridge: error en sync send: %s", e)
                self._failed_count += 1
                return ChannelResponse(
                    success=False,
                    channel=channel_name,
                    status=DeliveryStatus.FAILED,
                    error=f"Sync send failed: {e}",
                    timestamp=time.time(),
                )

        if response.success:
            self._sent_count += 1
        else:
            self._failed_count += 1

        return response

    # ── Estadísticas ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Estadísticas del bridge de compatibilidad."""
        return {
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "registry_providers": self._registry.registered_channels,
            "registry_stats": self._registry.stats,
        }


__all__ = [
    "CompatibilityBridge",
    "alert_to_channel_msg",
    "channel_response_to_text_result",
    "text_message_to_channel_msg",
]
