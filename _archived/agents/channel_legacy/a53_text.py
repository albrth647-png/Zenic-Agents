"""A53 TextChannelAgent — Pipeline de texto seguro.

Flujo: sanitize→limit→truncate/split→route→deliver→fallback

Reglas:
- Todo texto se sanitiza (sin inyecciones, sin caracteres de control)
- Límites estrictos (max length por canal)
- Si un canal falla, fallback a otro
- La IA NUNCA genera contenido — solo el SafetyGate decide YES/NO
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"
    SMS = "sms"


# Límites por canal
CHANNEL_LIMITS: dict[ChannelType, int] = {
    ChannelType.WHATSAPP: 65536,
    ChannelType.TELEGRAM: 4096,
    ChannelType.WEB: 100000,
    ChannelType.SMS: 160,
}

# Patrón de sanitización
DANGEROUS_PATTERNS = [
    re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"),  # Caracteres de control
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),  # XSS
    re.compile(r"javascript:", re.IGNORECASE),  # JS protocol
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
]


@dataclass
class TextMessage:
    """Mensaje de texto entrante/saliente."""

    channel: ChannelType
    recipient: str
    text: str
    sender: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    is_proactive: bool = False  # True si viene del SNA/Autopilot


@dataclass
class TextResult:
    """Resultado del pipeline de texto."""

    success: bool
    delivered: bool = False
    sanitized_text: str = ""
    chunks_sent: int = 0
    fallback_used: bool = False
    fallback_channel: ChannelType | None = None
    error: str = ""
    original: TextMessage | None = None


class TextChannelAgent:
    """A53 — Pipeline de procesamiento de mensajes de texto.

    sanitize → limit → truncate/split → route → deliver → fallback

    Determinista: No usa IA. Todo son reglas y límites.
    La IA solo actúa en el SafetyGate (YES/NO).
    """

    def __init__(self, fallback_channel: ChannelType = ChannelType.WEB):
        self.fallback_channel = fallback_channel
        logger.info(f"A53 TextChannelAgent inicializado (fallback={fallback_channel.value})")

    def process(self, message: TextMessage) -> TextResult:
        """Pipeline completo: sanitize→limit→truncate/split→route→deliver→fallback."""
        try:
            # Step 1: Sanitize
            sanitized = self._sanitize(message.text)

            # Step 2: Check limits
            limit = CHANNEL_LIMITS.get(message.channel, 4096)

            # Step 3: Split if needed
            chunks = self._split(sanitized, limit)

            # Step 4: Deliver
            delivered = self._deliver(message, chunks)

            if delivered:
                return TextResult(
                    success=True,
                    delivered=True,
                    sanitized_text=sanitized,
                    chunks_sent=len(chunks),
                    original=message,
                )

            # Step 5: Fallback
            fallback_delivered = self._fallback(message, chunks)

            return TextResult(
                success=fallback_delivered,
                delivered=fallback_delivered,
                sanitized_text=sanitized,
                chunks_sent=len(chunks) if fallback_delivered else 0,
                fallback_used=True,
                fallback_channel=self.fallback_channel if fallback_delivered else None,
                original=message,
            )

        except Exception as e:
            logger.error(f"Error al procesar mensaje de texto: {e}")
            return TextResult(
                success=False,
                error=str(e),
                original=message,
            )

    def _sanitize(self, text: str) -> str:
        """Sanitiza texto eliminando patrones peligrosos."""
        result = text
        for pattern in DANGEROUS_PATTERNS:
            result = pattern.sub("", result)

        # Eliminar espacios múltiples
        result = re.sub(r"\s+", " ", result).strip()

        # Limitar a max general
        if len(result) > 100000:
            result = result[:100000] + "... [el mensaje es muy largo, lo cortamos aquí]"

        return result

    def _split(self, text: str, limit: int) -> list[str]:
        """Divide texto en chunks que caben en el límite del canal."""
        if len(text) <= limit:
            return [text]

        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= limit:
                chunks.append(remaining)
                break

            # Buscar un punto de corte natural
            split_at = limit
            for sep in ["\n", ". ", " ", ""]:
                pos = remaining[:limit].rfind(sep)
                if pos > limit * 0.5:
                    split_at = pos + len(sep)
                    break

            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:]

        return chunks

    def _deliver(self, message: TextMessage, chunks: list[str]) -> bool:
        """Entrega mensaje al canal. En producción, usa la API del canal."""
        channel = message.channel.value
        recipient = message.recipient

        # En producción, usar la API real del canal
        logger.info(f"Entregado a {channel}:{recipient} — {len(chunks)} parte(s)")
        return True  # Simulado

    def _fallback(self, message: TextMessage, chunks: list[str]) -> bool:
        """Fallback a canal alternativo si el primario falla."""
        logger.warning(f"Reintentando por {self.fallback_channel.value} (fallback desde {message.channel.value})")
        # En producción, reintentar en el canal de fallback
        return True  # Simulado
