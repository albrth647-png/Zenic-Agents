"""ZENIC-AGENTS - Channel Formatter

Re-exports all formatting functions and classes.
"""

from ._discord import build_discord_confirmation_components, build_discord_embed, format_discord_message
from ._email import format_email_confirmation_html, format_email_html
from ._helpers import _parse_color, _store_and_replace
from ._limits import LIMITS, PlatformLimits
from ._push import format_push_confirmation_payload, format_push_payload
from ._slack import build_slack_blocks, build_slack_confirmation_blocks, escape_slack_text, format_slack_message
from ._sms import format_sms_text
from ._teams import build_teams_adaptive_card, build_teams_confirmation_card, format_teams_message
from ._telegram import build_telegram_inline_keyboard, escape_telegram_markdown_v2, format_telegram_message
from ._text import sanitize_html, sanitize_plain_text, split_message, truncate
from ._whatsapp import build_whatsapp_interactive_buttons, format_whatsapp_text
from ._wrapper import MessageFormatter

__all__ = [
    "LIMITS",
    "MessageFormatter",
    "PlatformLimits",
    "_parse_color",
    "_store_and_replace",
    "build_discord_confirmation_components",
    "build_discord_embed",
    "build_slack_blocks",
    "build_slack_confirmation_blocks",
    "build_teams_adaptive_card",
    "build_teams_confirmation_card",
    "build_telegram_inline_keyboard",
    "build_whatsapp_interactive_buttons",
    "escape_slack_text",
    "escape_telegram_markdown_v2",
    "format_discord_message",
    "format_email_confirmation_html",
    "format_email_html",
    "format_push_confirmation_payload",
    "format_push_payload",
    "format_slack_message",
    "format_sms_text",
    "format_teams_message",
    "format_telegram_message",
    "format_whatsapp_text",
    "sanitize_html",
    "sanitize_plain_text",
    "split_message",
    "truncate",
]
