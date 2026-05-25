"""ZENIC-AGENTS - Channel Formatter: MessageFormatter"""

from __future__ import annotations

from ._discord import build_discord_confirmation_components, build_discord_embed, format_discord_message
from ._email import format_email_confirmation_html, format_email_html
from ._limits import LIMITS
from ._push import format_push_confirmation_payload, format_push_payload
from ._slack import build_slack_blocks, build_slack_confirmation_blocks, escape_slack_text, format_slack_message
from ._sms import format_sms_text
from ._teams import build_teams_adaptive_card, build_teams_confirmation_card, format_teams_message
from ._telegram import build_telegram_inline_keyboard, escape_telegram_markdown_v2, format_telegram_message
from ._text import sanitize_html, sanitize_plain_text, split_message, truncate
from ._whatsapp import build_whatsapp_interactive_buttons, format_whatsapp_text


class MessageFormatter:
    """Stateless convenience wrapper for all formatting functions.

    All methods are static — no instance state.
    Use directly: MessageFormatter.format_telegram(msg)
    """

    # Platform limits
    limits = LIMITS

    # Text utilities
    truncate = staticmethod(truncate)
    split_message = staticmethod(split_message)
    sanitize_plain_text = staticmethod(sanitize_plain_text)
    sanitize_html = staticmethod(sanitize_html)

    # Telegram
    escape_telegram_markdown_v2 = staticmethod(escape_telegram_markdown_v2)
    format_telegram_message = staticmethod(format_telegram_message)
    build_telegram_inline_keyboard = staticmethod(build_telegram_inline_keyboard)

    # Discord
    build_discord_embed = staticmethod(build_discord_embed)
    build_discord_confirmation_components = staticmethod(build_discord_confirmation_components)
    format_discord_message = staticmethod(format_discord_message)

    # Slack
    escape_slack_text = staticmethod(escape_slack_text)
    build_slack_blocks = staticmethod(build_slack_blocks)
    build_slack_confirmation_blocks = staticmethod(build_slack_confirmation_blocks)
    format_slack_message = staticmethod(format_slack_message)

    # Teams
    build_teams_adaptive_card = staticmethod(build_teams_adaptive_card)
    build_teams_confirmation_card = staticmethod(build_teams_confirmation_card)
    format_teams_message = staticmethod(format_teams_message)

    # WhatsApp
    format_whatsapp_text = staticmethod(format_whatsapp_text)
    build_whatsapp_interactive_buttons = staticmethod(build_whatsapp_interactive_buttons)

    # SMS
    format_sms_text = staticmethod(format_sms_text)

    # Email
    format_email_html = staticmethod(format_email_html)
    format_email_confirmation_html = staticmethod(format_email_confirmation_html)

    # Push
    format_push_payload = staticmethod(format_push_payload)
    format_push_confirmation_payload = staticmethod(format_push_confirmation_payload)


# ──────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────
