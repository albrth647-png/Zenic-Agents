"""ZENIC-AGENTS - Channel Formatter: Slack"""

from __future__ import annotations

from typing import Any

from .._types import ChannelMessage, ConfirmationRequest
from ._limits import LIMITS
from ._text import sanitize_html, sanitize_plain_text, truncate


def escape_slack_text(text: str) -> str:
    """Escape special characters for Slack mrkdwn format."""
    if not text:
        return ""
    # Escape & < > (Slack's required escapes)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def build_slack_blocks(message: ChannelMessage) -> list[dict[str, Any]]:
    """Build Slack Block Kit blocks from a ChannelMessage.

    Returns:
        List of Block Kit block dicts.
    """
    blocks: list[dict[str, Any]] = []

    # Header block
    if message.title:
        blocks.append(
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": truncate(message.title, 150),
                },
            }
        )

    # Section block with text
    text = message.text or message.html
    if text:
        clean_text = sanitize_plain_text(text) if message.text else sanitize_html(text)
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": truncate(escape_slack_text(clean_text), LIMITS.slack_block_text),
                },
            }
        )

    # Fields block
    if message.fields:
        fields = []
        for f in message.fields[:10]:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*{escape_slack_text(f.get('title', f.get('name', '')))}:*\n{escape_slack_text(f.get('value', ''))}",
                }
            )
        blocks.append({"type": "section", "fields": fields})

    # Image block
    if message.image_url:
        blocks.append(
            {
                "type": "image",
                "image_url": message.image_url,
                "alt_text": message.title or "Image",
            }
        )

    # Context block (footer)
    if message.footer:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": truncate(escape_slack_text(message.footer), 2000),
                    }
                ],
            }
        )

    return blocks


def build_slack_confirmation_blocks(
    request: ConfirmationRequest,
    action_id_prefix: str = "confirm",
) -> list[dict[str, Any]]:
    """Build Slack Block Kit blocks for a confirmation request.

    Args:
        request: The confirmation request with options.
        action_id_prefix: Prefix for action_id values.

    Returns:
        List of Block Kit block dicts with confirmation buttons.
    """
    blocks: list[dict[str, Any]] = []

    # Message text
    if request.message:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": request.message},
            }
        )

    # Action block with buttons
    elements: list[dict[str, Any]] = []
    for option in request.options:
        label = option.replace("_", " ").title()
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": label},
                "value": f"{request.action_id}:{option}",
                "action_id": f"{action_id_prefix}_{option}",
            }
        )

    if elements:
        blocks.append({"type": "actions", "elements": elements})

    return blocks


def format_slack_message(message: ChannelMessage) -> dict[str, Any]:
    """Format a ChannelMessage into a Slack chat.postMessage payload."""
    blocks = build_slack_blocks(message)

    payload: dict[str, Any] = {}
    if blocks:
        payload["blocks"] = blocks
    else:
        text = message.text or message.html
        payload["text"] = truncate(
            sanitize_plain_text(text) if message.text else sanitize_html(text),
            LIMITS.slack_text,
        )

    if message.thread_id:
        payload["thread_ts"] = message.thread_id

    if message.reply_to:
        payload["thread_ts"] = message.reply_to

    return payload
