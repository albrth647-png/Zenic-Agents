"""
ZENIC-AGENTS — Unified Channel Manager (FASE 5).

Reemplaza el ChannelType.TELEGRAM hardcodeado por preferencias de canal
por tenant. Unifica los 4 canales legacy (whatsapp, telegram, web, sms)
con los 7 canales del NotificationDispatcher (email, push, webhook,
slack, teams, log).

Provee:
  - ChannelManager: envía por el canal preferido del tenant
  - TemplateEngine: mensajes por niche_id + idioma
  - BilingualBridge: detecta idioma antes de enviar
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import models

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# UNIFIED CHANNEL ENUM (11 canales)
# ══════════════════════════════════════════════════════════════


class UnifiedChannel(str, Enum):
    """Todos los canales disponibles, unificados.

    Fusiona los 4 de ChannelType (legacy) + los 7 de NotificationDispatcher.
    """

    # Legacy channels
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"
    SMS = "sms"

    # NotificationDispatcher channels
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    LOG = "log"

    # Especial
    NONE = "none"  # No enviar (solo registrar)


# ── Orden de prioridad para fallback ─────────────────────────

CHANNEL_PRIORITY: dict[UnifiedChannel, int] = {
    UnifiedChannel.WHATSAPP: 1,
    UnifiedChannel.TELEGRAM: 2,
    UnifiedChannel.SMS: 3,
    UnifiedChannel.EMAIL: 4,
    UnifiedChannel.PUSH: 5,
    UnifiedChannel.SLACK: 6,
    UnifiedChannel.TEAMS: 7,
    UnifiedChannel.WEBHOOK: 8,
    UnifiedChannel.WEB: 9,
    UnifiedChannel.LOG: 10,
    UnifiedChannel.NONE: 99,
}

DEFAULT_FALLBACK_CHAIN: list[UnifiedChannel] = [
    UnifiedChannel.WHATSAPP,
    UnifiedChannel.TELEGRAM,
    UnifiedChannel.SMS,
    UnifiedChannel.EMAIL,
    UnifiedChannel.LOG,
]


# ══════════════════════════════════════════════════════════════
# MESSAGE TEMPLATES (por niche_id + idioma)
# ══════════════════════════════════════════════════════════════


@dataclass
class MessageTemplate:
    """Template de mensaje para un nicho e idioma."""

    niche_id: str
    language: str  # "es" | "en"
    greeting: str = ""
    notification: str = ""
    alert: str = ""
    confirmation: str = ""
    error: str = ""

    def render(self, template_key: str, **kwargs) -> str:
        """Renderiza un template reemplazando variables."""
        template = getattr(self, template_key, "")
        if not template:
            return ""
        for key, val in kwargs.items():
            template = template.replace(f"{{{key}}}", str(val))
        return template


# ── Templates por defecto (ES/EN) ─────────────────────────────

DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "es": {
        "greeting": "¡Hola! Soy Zenic, tu asistente de {company}. ¿En qué puedo ayudarte?",
        "notification": "Notificación de {company}: {message}",
        "alert": "⚠️ Alerta de {company}: {message}",
        "confirmation": "✅ Listo. Se ha completado: {action}",
        "error": "❌ Ups, algo salió mal al procesar: {action}. Ya lo estamos revisando.",
    },
    "en": {
        "greeting": "Hi! I'm Zenic, your {company} assistant. How can I help?",
        "notification": "{company} notification: {message}",
        "alert": "⚠️ {company} alert: {message}",
        "confirmation": "✅ Done. Completed: {action}",
        "error": "❌ Oops, something went wrong processing: {action}. We're on it.",
    },
}


# ══════════════════════════════════════════════════════════════
# TEMPLATE ENGINE
# ══════════════════════════════════════════════════════════════


class TemplateEngine:
    """Mensajes por niche_id + idioma con templates configurables."""

    def __init__(self) -> None:
        self._custom_templates: dict[str, MessageTemplate] = {}

    def get_template(
        self,
        niche_id: str,
        language: str = "es",
    ) -> MessageTemplate:
        """Retorna el template para un niche e idioma. Usa defaults si no hay custom."""
        key = f"{niche_id}:{language}"
        custom = self._custom_templates.get(key)
        if custom:
            return custom

        # Generar template por defecto
        defaults = DEFAULT_TEMPLATES.get(language, DEFAULT_TEMPLATES["es"])
        return MessageTemplate(
            niche_id=niche_id,
            language=language,
            greeting=defaults["greeting"],
            notification=defaults["notification"],
            alert=defaults["alert"],
            confirmation=defaults["confirmation"],
            error=defaults["error"],
        )

    def set_template(self, template: MessageTemplate) -> None:
        """Guarda un template custom para un niche+idioma."""
        key = f"{template.niche_id}:{template.language}"
        self._custom_templates[key] = template

    def render(
        self,
        niche_id: str,
        template_key: str,
        language: str = "es",
        **kwargs,
    ) -> str:
        """Renderiza un template con variables."""
        template = self.get_template(niche_id, language)
        return template.render(template_key, **kwargs)


# ══════════════════════════════════════════════════════════════
# BILINGUAL BRIDGE
# ══════════════════════════════════════════════════════════════


class BilingualBridge:
    """Detecta idioma del texto y elige el template correspondiente."""

    def __init__(self) -> None:
        # Spanish indicators (copy of BilingualRouter's keywords)
        self._es_indicators = {
            "el", "la", "los", "las", "un", "una", "unos", "unas",
            "de", "del", "en", "por", "para", "con", "sin", "sobre",
            "que", "como", "donde", "cuando", "cual", "quien",
            "crear", "hacer", "tener", "poder", "decir", "ver",
            "proyecto", "aplicacion", "funcion", "metodo", "clase",
            "base de datos", "interfaz", "usuario", "sistema",
            "necesito", "quiero", "deseo", "ayuda",
        }

    def detect_language(self, text: str) -> str:
        """Detecta idioma del texto: 'es' o 'en'."""
        if not text:
            return "es"
        words = text.lower().split()
        if not words:
            return "es"
        es_count = sum(1 for w in words if w in self._es_indicators)
        ratio = es_count / len(words)
        return "es" if ratio > 0.15 else "en"

    def choose_template_key(self, text: str, default: str = "notification") -> str:
        """Elige tipo de template según el contenido."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["error", "fail", "fallo", "error"]):
            return "error"
        if any(w in text_lower for w in ["alert", "alerta", "warning", "peligro"]):
            return "alert"
        if any(w in text_lower for w in ["ok", "listo", "done", "confirm"]):
            return "confirmation"
        return default


# ══════════════════════════════════════════════════════════════
# CHANNEL MANAGER
# ══════════════════════════════════════════════════════════════


class ChannelManager:
    """
    Orquesta el envío de mensajes por el canal preferido del tenant.

    Reemplaza:
      - ChannelType.TELEGRAM hardcodeado en _proactive.py
      - La cadena de fallback fija en _bootstrap.py
      - La selección manual de canal en NotificationDispatcher

    Flujo:
      1. Leer preferencias del tenant (channel_prefs DB)
      2. Elegir canal según prioridad del tenant
      3. Renderizar template según niche_id + idioma detectado
      4. Enviar por el canal (o fallback si falla)
      5. Registrar envío para tracking de uso (plan limits)
    """

    def __init__(self) -> None:
        self.template_engine = TemplateEngine()
        self.bilingual = BilingualBridge()
        self._sent_count = 0

    def get_tenant_channel(self, tenant_id: str) -> tuple[UnifiedChannel, str]:
        """
        Retorna el canal preferido del tenant y el recipient.

        Lee de tenant.channel_prefs en la DB. Si no hay preferencias,
        retorna el canal por defecto del plan del tenant.
        """
        tenant = models.get_tenant(tenant_id)
        if tenant is None:
            return UnifiedChannel.LOG, ""

        prefs = tenant.get("channel_prefs", {})
        channel_str = prefs.get("preferred_channel", "")
        recipient = prefs.get("recipient", "")

        if channel_str:
            try:
                return UnifiedChannel(channel_str), recipient
            except ValueError:
                pass

        # Default según plan
        plan = tenant.get("plan", "free")
        defaults = {
            "enterprise": (UnifiedChannel.WHATSAPP, ""),
            "pro": (UnifiedChannel.TELEGRAM, ""),
            "free": (UnifiedChannel.WEB, ""),
        }
        return defaults.get(plan, (UnifiedChannel.WEB, ""))

    def set_tenant_channel(
        self,
        tenant_id: str,
        preferred_channel: str,
        recipient: str = "",
        additional_channels: list[str] | None = None,
    ) -> dict | None:
        """
        Actualiza las preferencias de canal de un tenant.

        Valida que el canal exista en UnifiedChannel.
        """
        try:
            UnifiedChannel(preferred_channel)
        except ValueError:
            return None

        prefs = {
            "preferred_channel": preferred_channel,
            "recipient": recipient,
            "additional_channels": additional_channels or [],
        }
        return models.update_tenant(tenant_id, {"channel_prefs": prefs})

    def send(
        self,
        tenant_id: str,
        message: str = "",
        template_key: str = "notification",
        niche_id: str = "default",
        channel_override: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Envía un mensaje al tenant por su canal preferido.

        Args:
            tenant_id: ID del tenant destino
            message: Mensaje a enviar (se usa directo si no hay template_vars)
            template_key: Qué template usar (notification, alert, etc.)
            niche_id: ID del nicho para elegir template
            channel_override: Forzar canal específico
            template_vars: Dict con variables para renderizar template

        Returns:
            dict con {success, channel, recipient, sent_via}
        """
        # 1. Determinar canal
        if channel_override:
            try:
                channel = UnifiedChannel(channel_override)
            except ValueError:
                channel = UnifiedChannel.LOG
            tenant = models.get_tenant(tenant_id)
            prefs = tenant.get("channel_prefs", {}) if tenant else {}
            recipient = prefs.get("recipient", "")
        else:
            channel, recipient = self.get_tenant_channel(tenant_id)

        if channel == UnifiedChannel.NONE:
            return {
                "success": True,
                "channel": "none",
                "recipient": "",
                "sent_via": "logged_only",
                "message": message,
            }

        # 2. Detectar idioma y renderizar template si hay variables
        detected_lang = self.bilingual.detect_language(message)
        if template_vars:
            message = self.template_engine.render(
                niche_id=niche_id,
                template_key=template_key,
                language=detected_lang,
                **(template_vars),
            )

        # 3. Enviar
        sent_via = self._dispatch(channel, recipient, message)

        # 4. Registrar envío exitoso
        if sent_via is not None:
            self._sent_count += 1
            models.increment_usage(tenant_id, "messages_sent")

        return {
            "success": sent_via is not None,
            "channel": channel.value,
            "recipient": recipient,
            "sent_via": sent_via or "none",
            "message": message,
            "language": detected_lang,
            "template_key": template_key,
            "niche_id": niche_id,
        }

    def send_with_fallback(
        self,
        tenant_id: str,
        message: str = "",
        template_key: str = "notification",
        niche_id: str = "default",
        channel_override: str | None = None,
        template_vars: dict[str, Any] | None = None,
        fallback_chain: list[UnifiedChannel] | None = None,
    ) -> dict[str, Any]:
        """
        Envía un mensaje con cadena de fallback.

        Intenta primero el canal preferido del tenant.
        Si falla, prueba los siguientes en la cadena.
        """
        primary = self.send(
            tenant_id, message,
            template_key=template_key,
            niche_id=niche_id,
            channel_override=channel_override,
            template_vars=template_vars,
        )
        if primary.get("success") and primary.get("channel") != "none":
            return primary

        chain = fallback_chain or DEFAULT_FALLBACK_CHAIN
        for ch in chain:
            result = self.send(
                tenant_id,
                message,
                template_key=template_key,
                niche_id=niche_id,
                channel_override=ch.value,
                template_vars=template_vars,
            )
            if result.get("success"):
                result["fallback_used"] = True
                return result

        return {
            "success": False,
            "channel": "none",
            "error": "All channels failed",
        }

    # ── Internal dispatch ────────────────────────────────────

    def _dispatch(
        self,
        channel: UnifiedChannel,
        recipient: str,
        message: str,
    ) -> str | None:
        """
        Envía el mensaje por el canal indicado.

        En producción, aquí irían las llamadas reales a APIs
        (Twilio, Telegram Bot API, SendGrid, Slack Webhook, etc.)
        """
        if channel == UnifiedChannel.NONE:
            return "logged_only"
        if channel == UnifiedChannel.LOG:
            logger.info(f"[LOG] {message}")
            return "log"

        # Simulación de envío exitoso
        logger.info(
            "📨 Enviado a %s:%s — %s...",
            channel.value,
            recipient or "(sin recipient)",
            message[:60],
        )
        return channel.value

    def get_stats(self) -> dict[str, Any]:
        """
        Retorna estadísticas del ChannelManager.
        """
        return {
            "total_sent": self._sent_count,
            "available_channels": [c.value for c in UnifiedChannel],
            "fallback_chain": [c.value for c in DEFAULT_FALLBACK_CHAIN],
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_channel_manager: ChannelManager | None = None


def get_channel_manager() -> ChannelManager:
    """Retorna el singleton del ChannelManager."""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChannelManager()
    return _channel_manager


def reset_channel_manager() -> None:
    """Resetea el singleton (para tests)."""
    global _channel_manager
    _channel_manager = None
