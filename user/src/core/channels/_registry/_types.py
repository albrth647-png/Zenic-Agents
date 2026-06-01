"""
ZENIC-AGENTS — Adapter Registry Types

Routing constants and type aliases for the channel registry.
"""

from __future__ import annotations

from .._types import ChannelPriority

# Priority → channel suitability mapping
_PRIORITY_CHANNEL_MAP: dict[ChannelPriority, list[str]] = {
    ChannelPriority.LOW: ["log", "email", "push"],
    ChannelPriority.NORMAL: ["log", "email", "push", "telegram", "teams", "slack"],
    ChannelPriority.HIGH: ["telegram", "email", "push", "teams", "slack", "sms"],
    ChannelPriority.URGENT: ["sms", "push", "telegram", "whatsapp", "teams", "slack", "email"],
    ChannelPriority.EMERGENCY: ["sms", "whatsapp", "telegram", "push", "teams", "slack", "email"],
}

# Default fallback chains
_DEFAULT_FALLBACKS: dict[str, list[str]] = {
    "teams": ["email", "log"],
    "slack": ["email", "log"],
    "telegram": ["whatsapp", "sms", "email", "log"],
    "whatsapp": ["telegram", "sms", "email", "log"],
    "sms": ["telegram", "email", "log"],
    "email": ["telegram", "push", "log"],
    "push": ["email", "log"],
    "log": [],
}
__all__ = ["_DEFAULT_FALLBACKS", "_PRIORITY_CHANNEL_MAP"]
