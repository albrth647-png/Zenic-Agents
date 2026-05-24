"""
A53 TextChannelAgent — SINGLE RESPONSIBILITY: Transport text through channels.

Deterministic text delivery pipeline:
  sanitize → limit-check → truncate/split → build messages → route → deliver → fallback

This agent is NOT a chatbot. It does not generate content.
It moves text from the core to the outside world through the channel system.

Design invariants:
  1. execute() NEVER raises — all errors captured in TextChannelResult.
  2. Core system NEVER knows if input came as text or voice.
  3. Every delivery is audited via BaseAgent.run() resilience wrapper.
  4. Fallback is always available — at minimum, the 'log' provider.
  5. Deterministic by design — no AI calls.
  6. Thread-safe — registry/router access is protected by their own locks.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
from typing import Any, Dict, List, Optional

from ..resilience import BaseAgent
from ..schemas.types._transport_types import TextChannelInput, TextChannelResult

# ──────────────────────────────────────────────────────────────
#  LAZY IMPORTS — avoid circular dependency at module level
# ──────────────────────────────────────────────────────────────

_logger = logging.getLogger("zenic_agents.agents.transport.text_channel")

# Module-level references (resolved on first use)
_registry_cls = None          # AdapterRegistry
_router_cls = None            # ChannelRouter
_channel_message_cls = None   # ChannelMessage
_channel_priority_cls = None  # ChannelPriority
_delivery_status_cls = None   # DeliveryStatus
_formatter_text = None        # sanitize_plain_text, truncate, split_message, LIMITS


def _resolve_deps() -> None:
    """Resolve channel dependencies lazily (once).

    This avoids circular imports at module load time while keeping
    the agent fully wired to the channel infrastructure at runtime.
    """
    global _registry_cls, _router_cls, _channel_message_cls
    global _channel_priority_cls, _delivery_status_cls
    global _formatter_text

    if _registry_cls is not None:
        return  # Already resolved

    from src.core.channels._registry import AdapterRegistry as _AR
    from src.core.channels._registry import ChannelRouter as _CR
    from src.core.channels._types import (
        ChannelMessage as _CM,
        ChannelPriority as _CP,
        DeliveryStatus as _DS,
    )
    from src.core.channels._formatter import (
        sanitize_plain_text as _spt,
        truncate as _tr,
        split_message as _sm,
        LIMITS as _L,
    )

    _registry_cls = _AR
    _router_cls = _CR
    _channel_message_cls = _CM
    _channel_priority_cls = _CP
    _delivery_status_cls = _DS
    _formatter_text = type("_Fmt", (), {
        "sanitize_plain_text": staticmethod(_spt),
        "truncate": staticmethod(_tr),
        "split_message": staticmethod(_sm),
        "LIMITS": _L,
    })()


# ──────────────────────────────────────────────────────────────
#  CHANNEL LIMIT MAPPING
# ──────────────────────────────────────────────────────────────

# Maps channel name → PlatformLimits attribute name
_CHANNEL_LIMIT_ATTR: Dict[str, str] = {
    "telegram": "telegram_text",
    "discord": "discord_text",
    "slack": "slack_text",
    "teams": "teams_text",
    "whatsapp": "whatsapp_text",
    "sms": "sms_text",
}

# Fallback limits for channels not in PlatformLimits
_FALLBACK_LIMITS: Dict[str, int] = {
    "email": 50_000,     # No practical limit for email body
    "push": 4_096,       # Typical push notification limit
    "log": 1_000_000,    # No limit for log provider
}

_DEFAULT_CHAR_LIMIT = 4_096  # Safe default for unknown channels


def _get_char_limit(channel: str) -> int:
    """Get the character limit for a specific channel.

    Uses PlatformLimits when available, falls back to
    _FALLBACK_LIMITS, then to _DEFAULT_CHAR_LIMIT.
    """
    _resolve_deps()
    limits_obj = _formatter_text.LIMITS

    attr_name = _CHANNEL_LIMIT_ATTR.get(channel)
    if attr_name and hasattr(limits_obj, attr_name):
        return getattr(limits_obj, attr_name)

    return _FALLBACK_LIMITS.get(channel, _DEFAULT_CHAR_LIMIT)


def _parse_priority(priority_str: str) -> Any:
    """Convert a priority string to ChannelPriority enum.

    Falls back to NORMAL for invalid values.
    """
    _resolve_deps()
    mapping = {
        "low": _channel_priority_cls.LOW,
        "normal": _channel_priority_cls.NORMAL,
        "high": _channel_priority_cls.HIGH,
        "urgent": _channel_priority_cls.URGENT,
        "emergency": _channel_priority_cls.EMERGENCY,
    }
    return mapping.get(priority_str.lower(), _channel_priority_cls.NORMAL)


# ──────────────────────────────────────────────────────────────
#  ASYNC BRIDGE
# ──────────────────────────────────────────────────────────────

def _run_async(coro: Any, timeout: float = 30.0) -> Any:
    """Bridge an async coroutine to synchronous execution.

    Handles two cases:
      1. No event loop running → asyncio.run()
      2. Event loop already running → ThreadPoolExecutor with new loop

    This is necessary because BaseAgent.execute() is synchronous,
    but channel send operations are async.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)

    # There IS a running loop — we must not block it.
    # Create a new loop in a separate thread.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=timeout)


# ──────────────────────────────────────────────────────────────
#  A53 TEXT CHANNEL AGENT
# ──────────────────────────────────────────────────────────────

class TextChannelAgent(BaseAgent[TextChannelResult]):
    """A53: Deterministic text transport agent.

    Single Responsibility: Deliver text through the channel system.
    Pipeline: sanitize → limit-check → truncate/split → route → deliver → fallback

    This agent is the ONLY way text leaves the core system.
    It ensures every outgoing text is:
      - Sanitized (no ANSI codes, no control chars)
      - Within platform limits (truncated or split)
      - Delivered with automatic fallback
      - Fully audited via BaseAgent resilience wrapper

    The agent receives a TextChannelInput with raw text and target channel,
    and returns a TextChannelResult with delivery status and metadata.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(name="A53_TextChannelAgent", **kwargs)
        self._registry: Optional[Any] = None   # AdapterRegistry — wired at startup
        self._router: Optional[Any] = None      # ChannelRouter — wired at startup

    # ── Dependency Wiring ─────────────────────────────────────

    def wire(
        self,
        registry: Any,       # AdapterRegistry
        router: Any = None,  # ChannelRouter (optional)
    ) -> None:
        """Wire channel infrastructure dependencies.

        Called during system startup by the orchestrator.
        The registry is REQUIRED — the router is optional
        (if not provided, direct channel delivery is used).

        Args:
            registry: AdapterRegistry instance for message delivery.
            router: ChannelRouter instance for priority-based routing.
        """
        _resolve_deps()
        self._registry = registry
        self._router = router
        _logger.info(
            "A53 wired: registry=%s, router=%s",
            type(registry).__name__ if registry else None,
            type(router).__name__ if router else None,
        )

    # ── Input Validation ──────────────────────────────────────

    def _validate_input(self, input_data: Any) -> TextChannelInput:
        """Normalize input to TextChannelInput.

        Accepts:
          - TextChannelInput instance (preferred)
          - dict with text/channel keys (convenience)
          - str (uses default channel → log)
        """
        if isinstance(input_data, TextChannelInput):
            return input_data

        if isinstance(input_data, dict):
            return TextChannelInput(
                text=input_data.get("text", ""),
                channel=input_data.get("channel", ""),
                recipient=input_data.get("recipient", ""),
                priority=input_data.get("priority", "normal"),
                reply_to=input_data.get("reply_to", ""),
                thread_id=input_data.get("thread_id", ""),
                metadata=input_data.get("metadata", {}),
                max_chunks=input_data.get("max_chunks", 10),
                fallback_channels=input_data.get("fallback_channels", ()),
            )

        # Plain string — log channel fallback
        if isinstance(input_data, str):
            return TextChannelInput(text=input_data, channel="log")

        # Fallback for unknown types
        return TextChannelInput(text=str(input_data), channel="log")

    # ── Core Execution ────────────────────────────────────────

    def execute(self, input_data: Any) -> TextChannelResult:
        """Execute the text delivery pipeline synchronously.

        Bridges to async internally. NEVER raises.
        All errors are captured in the returned TextChannelResult.
        """
        data = self._validate_input(input_data)
        _resolve_deps()

        # Fast path: no registry wired → fallback result
        if self._registry is None:
            _logger.warning("A53: registry not wired — returning fallback result")
            return self._make_result(
                data=data,
                success=False,
                error="Registry not wired — call wire() before execute()",
                source="deterministic",
            )

        try:
            return _run_async(self._deliver(data))
        except concurrent.futures.TimeoutError:
            return self._make_result(
                data=data,
                success=False,
                error="Delivery timed out",
                source="deterministic",
            )
        except Exception as e:
            return self._make_result(
                data=data,
                success=False,
                error=f"Delivery failed: {e}",
                source="deterministic",
            )

    async def _deliver(self, data: TextChannelInput) -> TextChannelResult:
        """Core async delivery pipeline.

        Steps:
          1. Sanitize raw text
          2. Resolve target channel (route if not specified)
          3. Get character limit for the channel
          4. Truncate or split text to fit
          5. Build ChannelMessage for each chunk
          6. Send via registry with automatic fallback
          7. Aggregate results into TextChannelResult
        """
        # ── Step 1: Sanitize ──
        sanitized = _formatter_text.sanitize_plain_text(data.text)
        if not sanitized.strip():
            return self._make_result(
                data=data,
                success=False,
                error="Empty text after sanitization",
            )

        # ── Step 2: Resolve channel ──
        channel = data.channel
        if not channel and self._router:
            priority = _parse_priority(data.priority)
            channels = self._router.route(priority=priority)
            channel = channels[0] if channels else "log"
        if not channel:
            channel = "log"

        # ── Step 3: Get char limit ──
        max_len = _get_char_limit(channel)

        # ── Step 4: Truncate or split ──
        original_len = len(sanitized)
        truncated = False

        if len(sanitized) > max_len:
            chunks = _formatter_text.split_message(sanitized, max_len)
            # Enforce max_chunks safety limit
            if len(chunks) > data.max_chunks:
                chunks = chunks[:data.max_chunks]
                # Truncate the last chunk to fit
                chunks[-1] = _formatter_text.truncate(chunks[-1], max_len)
                truncated = True
        else:
            chunks = [sanitized]

        total_chunks = len(chunks)

        # Add part indicators for split messages (e.g. "[1/3]")
        if total_chunks > 1:
            chunks = self._add_part_indicators(chunks, max_len)

        # ── Step 5: Send each chunk ──
        priority = _parse_priority(data.priority)
        results: List[Any] = []
        message_ids: List[str] = []

        for i, chunk in enumerate(chunks):
            msg = _channel_message_cls(
                text=chunk,
                recipient=data.recipient,
                reply_to=data.reply_to,
                thread_id=data.thread_id,
                priority=priority,
                metadata={
                    **data.metadata,
                    "_chunk_index": i,
                    "_chunk_total": total_chunks,
                    "_agent": "A53_TextChannelAgent",
                },
            )

            # Send with fallback chain
            response = await self._registry.send_with_fallback(channel, msg)
            results.append(response)

            if response.message_id:
                message_ids.append(response.message_id)

        # ── Step 6: Aggregate results ──
        all_success = all(r.success for r in results)
        any_fallback = any(
            r.status == _delivery_status_cls.FALLBACK for r in results
        )
        actual_channel = results[-1].channel if results else channel
        delivered_len = sum(len(c) for c in chunks)

        # Determine overall status
        if all_success:
            if any_fallback:
                status = "fallback"
            else:
                status = "sent"
        else:
            status = "failed"

        return self._make_result(
            data=data,
            success=all_success,
            channel_used=actual_channel,
            original_channel=channel,
            messages_sent=sum(1 for r in results if r.success),
            message_ids=message_ids,
            status=status,
            truncated=truncated,
            split_count=total_chunks,
            fallback_used=any_fallback,
            original_length=original_len,
            delivered_length=delivered_len,
            error="; ".join(r.error for r in results if r.error) if not all_success else "",
        )

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _add_part_indicators(chunks: List[str], max_len: int) -> List[str]:
        """Add [N/M] part indicators to split messages.

        Adds a part indicator at the beginning of each chunk,
        respecting the character limit. Only applied when there
        are 2+ chunks.
        """
        total = len(chunks)
        if total <= 1:
            return chunks

        result: List[str] = []
        for i, chunk in enumerate(chunks, start=1):
            indicator = f"[{i}/{total}] "
            # Only add indicator if it fits (with safety margin)
            if len(indicator) + len(chunk) <= max_len:
                result.append(indicator + chunk)
            else:
                result.append(chunk)
        return result

    @staticmethod
    def _make_result(
        data: TextChannelInput,
        success: bool = False,
        channel_used: str = "",
        original_channel: str = "",
        messages_sent: int = 0,
        message_ids: Optional[List[str]] = None,
        status: str = "pending",
        truncated: bool = False,
        split_count: int = 0,
        fallback_used: bool = False,
        original_length: int = 0,
        delivered_length: int = 0,
        error: str = "",
        source: str = "deterministic",
    ) -> TextChannelResult:
        """Build a TextChannelResult with sensible defaults."""
        return TextChannelResult(
            success=success,
            channel_used=channel_used or data.channel or "log",
            original_channel=original_channel or data.channel,
            messages_sent=messages_sent,
            message_ids=message_ids or [],
            status=status,
            truncated=truncated,
            split_count=split_count,
            fallback_used=fallback_used,
            original_length=original_length or len(data.text),
            delivered_length=delivered_length,
            error=error,
            source=source,
        )

    # ── Fallback ──────────────────────────────────────────────

    def fallback(self, input_data: Any) -> TextChannelResult:
        """Deterministic fallback when execute() fails.

        Returns a safe result indicating delivery was not attempted.
        The message is logged for later retry.
        """
        data = self._validate_input(input_data)
        _logger.info(
            "A53 fallback: text_len=%d, channel=%s",
            len(data.text),
            data.channel or "(none)",
        )
        return TextChannelResult(
            success=False,
            channel_used="log",
            original_channel=data.channel,
            messages_sent=0,
            message_ids=[],
            status="fallback",
            truncated=False,
            split_count=0,
            fallback_used=False,
            original_length=len(data.text),
            delivered_length=0,
            error="Agent fallback — delivery not attempted",
            source="fallback",
        )

    # ── Async Entry Point ─────────────────────────────────────

    async def deliver(self, input_data: Any) -> TextChannelResult:
        """Async entry point for direct async callers.

        Use this when calling from an async context to avoid
        the sync-async bridge overhead. This is the preferred
        entry point for async orchestrators.

        Args:
            input_data: TextChannelInput, dict, or str.

        Returns:
            TextChannelResult with delivery outcome.
        """
        data = self._validate_input(input_data)
        _resolve_deps()

        if self._registry is None:
            return self._make_result(
                data=data,
                success=False,
                error="Registry not wired — call wire() before deliver()",
            )

        try:
            return await self._deliver(data)
        except Exception as e:
            return self._make_result(
                data=data,
                success=False,
                error=f"Async delivery failed: {e}",
            )
