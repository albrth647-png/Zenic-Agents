"""ZENIC-AGENTS - Channel Formatter: Sms"""

from __future__ import annotations

def format_sms_text(message: ChannelMessage) -> str:  # noqa: F821  # TODO: verify import
    """Format a ChannelMessage into a plain SMS string.  # noqa: F821  # TODO: verify import

    Strips all rich formatting, enforces 160-char limit per segment.
    """
    parts: List[str] = []  # noqa: F821  # TODO: verify import

    if message.title:
        parts.append(f"[{message.title}]")

    text = sanitize_plain_text(message.text)  # noqa: F821  # TODO: Phase3 - verify import
    if text:
        parts.append(text)

    if message.footer:
        parts.append(f"— {message.footer}")

    return " ".join(parts) if parts else ""


# ──────────────────────────────────────────────────────────────
#  EMAIL FORMATTING
# ──────────────────────────────────────────────────────────────
