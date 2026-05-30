"""ZENIC-AGENTS - Channel Formatter: Email"""

from __future__ import annotations

import html as html_module
from typing import TYPE_CHECKING

from ._text import sanitize_html

if TYPE_CHECKING:
    from .._types import ChannelMessage, ConfirmationRequest


def format_email_html(message: ChannelMessage) -> str:  # TODO: verify import
    """Format a ChannelMessage into an HTML email body.  # noqa: F821  # TODO: verify import

    Builds a styled HTML email with optional title, body,
    field table, and footer.
    """
    parts: list[str] = []  # TODO: verify import

    # Title
    if message.title:
        parts.append(
            f'<h2 style="color:#1a1a1a;margin:0 0 12px 0;">{html_module.escape(message.title)}</h2>'
        )  # TODO: verify import

    # Subtitle
    if message.subtitle:
        parts.append(
            f'<p style="color:#666;margin:0 0 8px 0;font-size:14px;">{html_module.escape(message.subtitle)}</p>'
        )  # TODO: verify import

    # Body
    if message.html:
        parts.append(f'<div style="margin:0 0 12px 0;">{sanitize_html(message.html)}</div>')  # TODO: verify import
    elif message.text:
        escaped = html_module.escape(message.text).replace("\n", "<br>")  # TODO: verify import
        parts.append(f'<div style="margin:0 0 12px 0;">{escaped}</div>')

    # Fields table
    if message.fields:
        rows = []
        for f in message.fields[:20]:
            key = html_module.escape(f.get("title", f.get("name", "")))  # TODO: verify import
            val = html_module.escape(str(f.get("value", "")))  # TODO: verify import
            rows.append(
                f'<tr><td style="padding:6px 12px;font-weight:bold;border-bottom:1px solid #eee;">{key}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #eee;">{val}</td></tr>'
            )
        parts.append(f'<table style="border-collapse:collapse;width:100%;margin:0 0 12px 0;">{"".join(rows)}</table>')

    # Image
    if message.image_url:
        alt_text = html_module.escape(message.title or "Image")  # TODO: verify import
        safe_url = html_module.escape(message.image_url, quote=True)  # TODO: verify import
        parts.append(f'<img src="{safe_url}" alt="{alt_text}" style="max-width:100%;margin:0 0 12px 0;" />')

    # Footer
    if message.footer:
        parts.append(
            f'<p style="color:#999;font-size:12px;margin:12px 0 0 0;">{html_module.escape(message.footer)}</p>'
        )  # TODO: verify import

    body = "\n".join(parts)
    return f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">{body}</div>'


def format_email_confirmation_html(request: ConfirmationRequest) -> str:  # TODO: verify import
    """Format a confirmation request as an HTML email with action buttons.

    Returns styled HTML with YES/NO/MORE_INFO links.
    """
    button_colors = {
        "yes": "#28a745",
        "no": "#dc3545",
        "more_info": "#6c757d",
    }
    button_labels = {
        "yes": "✅ Confirm",
        "no": "❌ Deny",
        "more_info": "ℹ️ More Info",
    }

    buttons = []
    for option in request.options:
        color = button_colors.get(option, "#007bff")
        label = button_labels.get(option, option.replace("_", " ").title())
        buttons.append(
            f'<a href="#action-{option}" style="display:inline-block;padding:10px 20px;'
            f"background-color:{color};color:white;text-decoration:none;border-radius:4px;"
            f'margin-right:8px;font-weight:bold;">{label}</a>'
        )

    return (
        f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
        f'<h2 style="color:#1a1a1a;">{html_module.escape(request.title)}</h2>'  # TODO: verify import
        f'<p style="color:#333;">{html_module.escape(request.message)}</p>'  # TODO: verify import
        f'<div style="margin:20px 0;">{"".join(buttons)}</div>'
        f'<p style="color:#999;font-size:12px;">Action ID: {html_module.escape(request.action_id)} | '  # TODO: Phase3 - verify import
        f"Expires in {request.timeout_seconds // 60} minutes</p>"
        f"</div>"
    )


# ──────────────────────────────────────────────────────────────
#  PUSH NOTIFICATION FORMATTING
# ──────────────────────────────────────────────────────────────
