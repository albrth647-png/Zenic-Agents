"""ProactiveChannelBridge — Conecta el sistema proactivo con los canales.

Este es el cable que falta entre:
    SNA/Autopilot (que ven datos LOCALES) → Canales (donde está el usuario)

Sin este bridge:
    SNA detecta stock bajo → Nobody knows → El usuario se entrena cuando se acaba

Con este bridge:
    SNA detecta stock bajo → AlertManager → ProactiveChannelBridge → WhatsApp → "Oye, stock bajo en X"

El bridge NO genera contenido. Solo transporta alertas ya formateadas.
La IA NUNCA escribe el mensaje — el AlertManager lo construye determinísticamente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.core.channel.a53_text import ChannelType, TextChannelAgent, TextMessage
from src.core.sna.alert_manager import Alert, AlertChannel, AlertSeverity

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


# Mapeo de canal de alerta → canal de entrega
ALERT_TO_CHANNEL: dict[AlertChannel, ChannelType] = {
    AlertChannel.WHATSAPP: ChannelType.WHATSAPP,
    AlertChannel.TELEGRAM: ChannelType.TELEGRAM,
    AlertChannel.LOG: ChannelType.WEB,  # LOG no es un canal real, usar WEB como fallback
}


@dataclass
class ProactiveMessage:
    """Mensaje proactivo listo para enviar."""

    text: str
    channel: ChannelType
    recipient: str
    severity: AlertSeverity
    source: str  # "sna" o "autopilot"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ProactiveResult:
    """Resultado del envío proactivo."""

    success: bool
    message: ProactiveMessage | None = None
    error: str = ""
    delivered: bool = False


class ProactiveChannelBridge:
    """Bridge entre SNA/Autopilot y los canales del usuario.

    Recibe alertas del SNA y las envía al canal configurado del usuario.
    NO genera contenido — solo transporta lo que el AlertManager construyó.
    """

    def __init__(
        self,
        text_agent: TextChannelAgent | None = None,
        default_channel: ChannelType = ChannelType.TELEGRAM,
        default_recipient: str = "",
    ):
        self.text_agent = text_agent or TextChannelAgent()
        self.default_channel = default_channel
        self.default_recipient = default_recipient

        # Estadísticas
        self._sent_count = 0
        self._failed_count = 0
        self._last_sent: datetime | None = None

        logger.info(f"ProactiveChannelBridge inicializado (canal default={default_channel.value})")

    def send_alert(self, alert: Alert) -> ProactiveResult:
        """Envía una alerta del SNA al canal del usuario."""
        # Determinar canal
        channel = ALERT_TO_CHANNEL.get(alert.channel, self.default_channel)

        # Si es LOG-only, no enviar a usuario
        if alert.channel == AlertChannel.LOG:
            logger.info(f"[LOG-ONLY] {alert.severity.value}: {alert.message}")
            return ProactiveResult(success=True, delivered=False)

        # Crear mensaje proactivo
        recipient = self.default_recipient
        if not recipient:
            logger.warning("No hay destinatario configurado para mensajes proactivos")
            return ProactiveResult(success=False, error="No recipient configured")

        proactive_msg = ProactiveMessage(
            text=alert.message,
            channel=channel,
            recipient=recipient,
            severity=alert.severity,
            source="sna",
        )

        # Enviar via A53
        text_msg = TextMessage(
            channel=channel,
            recipient=recipient,
            text=alert.message,
            is_proactive=True,
        )

        result = self.text_agent.process(text_msg)

        if result.success:
            self._sent_count += 1
            self._last_sent = datetime.now()
            logger.info(f"Alerta proactiva enviada: [{alert.severity.value}] {alert.monitor_name} → {channel.value}")
            return ProactiveResult(success=True, message=proactive_msg, delivered=True)

        self._failed_count += 1
        logger.error(f"Error enviando alerta proactiva: {result.error}")
        return ProactiveResult(success=False, error=result.error, message=proactive_msg)

    def send_notification(
        self, text: str, severity: AlertSeverity = AlertSeverity.INFO, source: str = "autopilot"
    ) -> ProactiveResult:
        """Envía una notificación del Autopilot al canal del usuario."""
        channel = self.default_channel
        if severity == AlertSeverity.CRITICAL:
            channel = ChannelType.WHATSAPP

        recipient = self.default_recipient
        if not recipient:
            return ProactiveResult(success=False, error="No recipient configured")

        proactive_msg = ProactiveMessage(
            text=text,
            channel=channel,
            recipient=recipient,
            severity=severity,
            source=source,
        )

        text_msg = TextMessage(
            channel=channel,
            recipient=recipient,
            text=text,
            is_proactive=True,
        )

        result = self.text_agent.process(text_msg)

        if result.success:
            self._sent_count += 1
            self._last_sent = datetime.now()
            return ProactiveResult(success=True, message=proactive_msg, delivered=True)

        self._failed_count += 1
        return ProactiveResult(success=False, error=result.error)

    def get_stats(self) -> dict[str, Any]:
        """Estadísticas del bridge."""
        return {
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "last_sent": self._last_sent.isoformat() if self._last_sent else None,
            "default_channel": self.default_channel.value,
            "default_recipient": self.default_recipient,
        }


class AutopilotChannelInterceptor:
    """Intercepta acciones del Autopilot que requieren notificación al usuario.

    El Autopilot ejecuta acciones automáticamente. Este interceptor
    notifica al usuario ANTES (si es SEMI_AUTONOMOUS) o DESPUÉS
    (si es FULL_AUTONOMOUS) de ejecutar.
    """

    def __init__(self, bridge: ProactiveChannelBridge):
        self.bridge = bridge
        logger.info("AutopilotChannelInterceptor inicializado")

    def notify_before_action(self, action: dict[str, Any], autonomy_level: str) -> bool:
        """Notifica al usuario antes de una acción. Retorna True si aprobado."""
        if autonomy_level == "SUPERVISED":
            # Siempre notificar y esperar aprobación
            self.bridge.send_notification(
                text=f"Autopilot solicita aprobación: {action.get('type', 'acción')} — {action.get('description', '')}",
                severity=AlertSeverity.WARNING,
                source="autopilot",
            )
            return False  # Requiere aprobación explícita

        if autonomy_level == "SEMI_AUTONOMOUS":
            # Notificar pero no bloquear para acciones de bajo riesgo
            risk = action.get("risk", "low")
            if risk == "high":
                self.bridge.send_notification(
                    text=f"Autopilot: acción de alto riesgo pendiente — {action.get('description', '')}",
                    severity=AlertSeverity.WARNING,
                    source="autopilot",
                )
                return False
            return True

        # FULL_AUTONOMOUS — no bloquear
        return True

    def notify_after_action(self, action: dict[str, Any], result: dict[str, Any]):
        """Notifica al usuario después de una acción ejecutada."""
        success = result.get("success", False)
        severity = AlertSeverity.INFO if success else AlertSeverity.WARNING

        self.bridge.send_notification(
            text=f"Autopilot: {'✓' if success else '✗'} {action.get('type', 'acción')} — {result.get('message', '')}",
            severity=severity,
            source="autopilot",
        )


def create_sna_callback(bridge: ProactiveChannelBridge) -> Callable[[Alert], None]:
    """Crea un callback para conectar SNA → ProactiveChannelBridge.

    Uso:
        bridge = ProactiveChannelBridge(...)
        engine = SNAEngine(on_alert=create_sna_callback(bridge))
    """

    def on_sna_alert(alert: Alert):
        bridge.send_alert(alert)

    return on_sna_alert
