"""
ZENIC-AGENTS — Unified Channel System

Phase 0: Infrastructure (ChannelProvider protocol, AdapterRegistry, ChannelRouter, MessageFormatter)
Phase 1: Providers (Teams, Slack, WhatsApp, Twilio SMS)
Phase 2: Providers (Email, Push Notifications)

Architecture:
  - ChannelProvider protocol → every provider implements the same interface
  - AdapterRegistry → dynamic registration + fallback routing (mirrors ExecutorRegistry)
  - ChannelRouter → priority-based routing with user preferences
  - MessageFormatter → cross-platform formatting (Markdown, embeds, cards, blocks)
  - LogChannelProvider → always-available terminal fallback
"""

# ── Phase 0: Core Infrastructure ──────────────────────────────

# Types
# Formatter
from ._formatter import (
    LIMITS,
    MessageFormatter,
    PlatformLimits,
    build_discord_confirmation_components,
    build_discord_embed,
    build_slack_blocks,
    build_slack_confirmation_blocks,
    build_teams_adaptive_card,
    build_teams_confirmation_card,
    build_telegram_inline_keyboard,
    build_whatsapp_interactive_buttons,
    escape_slack_text,
    escape_telegram_markdown_v2,
    format_discord_message,
    format_email_confirmation_html,
    # Email
    format_email_html,
    format_push_confirmation_payload,
    # Push
    format_push_payload,
    format_slack_message,
    format_sms_text,
    format_teams_message,
    format_telegram_message,
    format_whatsapp_text,
    sanitize_html,
    sanitize_plain_text,
    split_message,
    truncate,
)

# Log Provider (always available)
from ._log_provider import LogChannelProvider

# Protocol
from ._protocol import (
    ChannelProvider,
    InboundChannelProvider,
    can_receive_voice,
    can_send_confirmation,
    can_send_voice,
    has_capability,
    requires_inbound,
)

# Registry + Router
from ._registry import (
    AdapterRegistry,
    ChannelRouter,
    get_default_registry,
    get_default_router,
    reset_default_registry,
)
from ._types import (
    ChannelCapability,
    ChannelMessage,
    ChannelPriority,
    ChannelResponse,
    ConfirmationHandler,
    ConfirmationRequest,
    ConfirmationResult,
    DeliveryStatus,
    MessageHandler,
    ProviderConfig,
    RateLimitInfo,
)
from .providers.email import EmailChannelProvider
from .providers.push import PushChannelProvider
from .providers.slack import SlackChannelProvider

# ── Phase 1: Channel Providers ────────────────────────────────
from .providers.teams import TeamsChannelProvider
from .providers.twilio_sms import TwilioSMSChannelProvider
from .providers.whatsapp import WhatsAppChannelProvider

__all__ = [
    "LIMITS",
    # Registry + Router
    "AdapterRegistry",
    # Types
    "ChannelCapability",
    "ChannelMessage",
    "ChannelPriority",
    # Protocol
    "ChannelProvider",
    "ChannelResponse",
    "ChannelRouter",
    "ConfirmationHandler",
    "ConfirmationRequest",
    "ConfirmationResult",
    "DeliveryStatus",
    # Phase 2
    "EmailChannelProvider",
    "InboundChannelProvider",
    # Providers
    "LogChannelProvider",
    "MessageFormatter",
    "MessageHandler",
    # Formatter
    "PlatformLimits",
    "ProviderConfig",
    "PushChannelProvider",
    "RateLimitInfo",
    "SlackChannelProvider",
    "TeamsChannelProvider",
    "TwilioSMSChannelProvider",
    "WhatsAppChannelProvider",
    "build_discord_confirmation_components",
    "build_discord_embed",
    "build_slack_blocks",
    "build_slack_confirmation_blocks",
    "build_teams_adaptive_card",
    "build_teams_confirmation_card",
    "build_telegram_inline_keyboard",
    "build_whatsapp_interactive_buttons",
    "can_receive_voice",
    "can_send_confirmation",
    "can_send_voice",
    "escape_slack_text",
    "escape_telegram_markdown_v2",
    "format_discord_message",
    "format_email_confirmation_html",
    # Email
    "format_email_html",
    "format_push_confirmation_payload",
    # Push
    "format_push_payload",
    "format_slack_message",
    "format_sms_text",
    "format_teams_message",
    "format_telegram_message",
    "format_whatsapp_text",
    "get_default_registry",
    "get_default_router",
    "has_capability",
    "requires_inbound",
    "reset_default_registry",
    "sanitize_html",
    "sanitize_plain_text",
    "split_message",
    "truncate",
]
