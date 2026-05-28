"""
ZENIC-AGENTS — Channel Registry Helpers

Utility functions for channel registry operations: validation,
fallback chain resolution, response construction, and provider filtering.

These helpers factor out repetitive patterns from AdapterRegistry
and ChannelRouter without adding business logic to the core classes.
"""

from __future__ import annotations

import re

from .._types import ChannelPriority, ChannelResponse, DeliveryStatus
from ._types import _DEFAULT_FALLBACKS, _PRIORITY_CHANNEL_MAP

# ── Validation ───────────────────────────────────────────────

_VALID_CHANNEL_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_channel_name(name: str) -> bool:
    """Check if a channel name is valid.

    A valid channel name is non-empty, starts with a lowercase letter,
    and contains only lowercase alphanumeric characters and underscores.

    Args:
        name: Channel name to validate.

    Returns:
        True if the name is valid, False otherwise.
    """
    if not name:
        return False
    return bool(_VALID_CHANNEL_PATTERN.match(name))


# ── Fallback Resolution ─────────────────────────────────────


def resolve_fallback_chain(
    channel: str,
    custom_fallbacks: dict[str, list[str]] | None = None,
) -> list[str]:
    """Resolve the full fallback chain for a channel.

    Merges custom fallbacks with the default fallback map, always
    ensuring ``"log"`` appears as the terminal fallback unless it
    is the primary channel itself.

    Args:
        channel: Primary channel name.
        custom_fallbacks: Optional overrides for specific channels.

    Returns:
        Ordered list of fallback channel names (excluding the primary).
    """
    fallbacks: list[str] = list(
        (custom_fallbacks or {}).get(channel, _DEFAULT_FALLBACKS.get(channel, []))
    )
    # Guarantee terminal "log" fallback (unless the channel IS log)
    if channel != "log" and "log" not in fallbacks:
        fallbacks.append("log")
    return fallbacks


# ── Priority Mapping ────────────────────────────────────────


def channels_for_priority(priority: ChannelPriority) -> list[str]:
    """Return candidate channel list for a given priority level.

    Args:
        priority: The message priority level.

    Returns:
        List of channel names suitable for the priority, ordered by
        preference.  Returns an empty list for unknown priorities.
    """
    return list(_PRIORITY_CHANNEL_MAP.get(priority, []))


# ── Provider Filtering ──────────────────────────────────────


def filter_available_channels(
    candidates: list[str],
    available_providers: dict[str, bool],
    exclude: set[str] | None = None,
) -> list[str]:
    """Filter candidate channel list to only available and non-excluded ones.

    Args:
        candidates: Ordered list of candidate channel names.
        available_providers: Mapping of channel name to availability
            (True = registered and healthy).
        exclude: Optional set of channel names to exclude.

    Returns:
        Filtered list preserving the original candidate order.
    """
    excluded = exclude or set()
    return [
        ch
        for ch in candidates
        if ch not in excluded and available_providers.get(ch, False)
    ]


# ── Response Construction ───────────────────────────────────


def build_failed_response(channel: str, error: str) -> ChannelResponse:
    """Construct a standard failed ChannelResponse for registry-level errors.

    Used when a message cannot be delivered because the channel is
    unavailable, unregistered, or encounters an infrastructure error.

    Args:
        channel: The channel name that failed.
        error: Human-readable error description.

    Returns:
        A ChannelResponse with ``success=False`` and ``status=FAILED``.
    """
    return ChannelResponse(
        success=False,
        channel=channel,
        status=DeliveryStatus.FAILED,
        error=error,
    )


def build_fallback_response(
    original_channel: str,
    fallback_channel: str,
    inner: ChannelResponse,
) -> ChannelResponse:
    """Construct a fallback ChannelResponse with routing metadata.

    Wraps the response from the fallback channel with metadata
    indicating the original intended channel and the fallback used.

    Args:
        original_channel: The channel that was initially targeted.
        fallback_channel: The channel that actually handled delivery.
        inner: The response from the fallback channel send.

    Returns:
        A ChannelResponse with ``status=FALLBACK`` and routing metadata.
    """
    return ChannelResponse(
        success=inner.success,
        channel=fallback_channel,
        message_id=inner.message_id,
        status=DeliveryStatus.FALLBACK,
        error=inner.error,
        metadata={
            **inner.metadata,
            "original_channel": original_channel,
            "fallback_channel": fallback_channel,
        },
        timestamp=inner.timestamp,
    )


# ── User Preference Reordering ──────────────────────────────


def merge_user_preferences(
    candidates: list[str],
    user_channels: list[str],
) -> list[str]:
    """Reorder candidates to prioritize user-preferred channels.

    User-preferred channels are moved to the front of the list while
    preserving the relative order of non-preferred channels.

    Args:
        candidates: System-determined candidate channel list.
        user_channels: Channels the user has explicitly enabled/prioritized.

    Returns:
        Reordered list with user preferences first.
    """
    preferred_set = set(user_channels)
    preferred: list[str] = [ch for ch in candidates if ch in preferred_set]
    remaining: list[str] = [ch for ch in candidates if ch not in preferred_set]
    return preferred + remaining


# ── Public Exports ──────────────────────────────────────────

__all__ = [
    "build_failed_response",
    "build_fallback_response",
    "channels_for_priority",
    "filter_available_channels",
    "merge_user_preferences",
    "resolve_fallback_chain",
    "validate_channel_name",
]
