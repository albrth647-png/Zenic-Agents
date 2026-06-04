"""
ZENIC-AGENTS — Async Event Bus (SSE Bridge).

In-memory pub/sub bridge between synchronous agent components and
async SSE consumers. Each channel has an asyncio.Queue that SSE
clients consume from. Agents publish events via publish().

Protection:
  - Max subscribers per channel: 10
  - Max queue size: 100 events
  - All queue operations are async-locked
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)

# ── Event types ───────────────────────────────────────────────

EVENT_NOTIFICATION = "notification"
EVENT_COLLECTOR = "collector"
EVENT_SYSTEM = "system"
EVENT_KEEPALIVE = "keepalive"

# ── Limits ────────────────────────────────────────────────────

_MAX_SUBSCRIBERS_PER_CHANNEL: int = 10
_MAX_QUEUE_SIZE: int = 100
_MAX_IDLE_SECONDS: float = 300.0
_KEEPALIVE_INTERVAL: float = 15.0


# ── Event dataclass ───────────────────────────────────────────

class StreamEvent:
    """Represents a single SSE event."""

    __slots__ = ("event_type", "data", "channel", "timestamp")

    def __init__(
        self,
        event_type: str,
        data: dict[str, Any],
        channel: str = "",
    ) -> None:
        self.event_type = event_type
        self.data = data
        self.channel = channel
        self.timestamp = time.monotonic()

    def to_sse(self) -> str:
        """Serialize to SSE format."""
        payload = json.dumps(self.data)
        lines = [
            f"event: {self.event_type}",
            f"data: {payload}",
            "",
        ]
        return "\n".join(lines)


# ── Keep-alive event ──────────────────────────────────────────

_KEEPALIVE = StreamEvent(EVENT_KEEPALIVE, {"type": "ping"})


# ── Event Bus ─────────────────────────────────────────────────

class EventBus:
    """
    In-memory async pub/sub event bus.

    Channels:
      - "tenant:{tenant_id}" — tenant-level notifications
      - "collector:{session_id}" — collector session updates
      - "system:global" — global system events

    Usage:
        bus = get_event_bus()
        await bus.publish("tenant:abc", "notification", {"msg": "Hello"})
        async for event in bus.subscribe("tenant:abc"):
            print(event.to_sse())
    """

    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def publish(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Publish an event to a channel and all its subscribers.

        Args:
            channel: Channel name (e.g., "tenant:abc", "collector:sess_123")
            event_type: Event type string
            data: Event payload dict

        Returns:
            Number of subscribers that received the event.
        """
        event = StreamEvent(event_type=event_type, data=data, channel=channel)
        delivered = 0

        async with self._lock:
            queues = self._queues.get(channel, set()).copy()

        for queue in queues:
            try:
                await asyncio.wait_for(queue.put(event), timeout=1.0)
                delivered += 1
            except (asyncio.TimeoutError, Exception):
                pass  # Queue full or closed — subscriber is too slow

        return delivered

    async def subscribe(
        self,
        channel: str,
    ) -> asyncio.Queue:
        """
        Subscribe to a channel. Returns an asyncio.Queue.

        Raises RuntimeError if channel already has _MAX_SUBSCRIBERS_PER_CHANNEL.
        The caller must call unsubscribe() when done.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)

        async with self._lock:
            subscribers = self._queues.get(channel, set())
            if len(subscribers) >= _MAX_SUBSCRIBERS_PER_CHANNEL:
                raise RuntimeError(
                    f"Channel '{channel}' has reached max subscribers "
                    f"({_MAX_SUBSCRIBERS_PER_CHANNEL})"
                )
            subscribers.add(queue)
            self._queues[channel] = subscribers

        logger.debug("Subscribed to channel: %s (total: %d)", channel, len(self._queues.get(channel, set())))
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        """Unsubscribe a queue from a channel."""
        async with self._lock:
            if channel in self._queues:
                self._queues[channel].discard(queue)
                if not self._queues[channel]:
                    del self._queues[channel]

        logger.debug("Unsubscribed from channel: %s", channel)

    def channel_count(self) -> dict[str, int]:
        """Return subscriber count per channel (copy for safety)."""
        return {ch: len(qs) for ch, qs in self._queues.copy().items()}

    @property
    def total_subscribers(self) -> int:
        """Return total number of active subscribers."""
        return sum(len(qs) for qs in self._queues.copy().values())


# ── Singleton ─────────────────────────────────────────────────

_event_bus: EventBus | None = None
_bus_lock = asyncio.Lock()


async def get_event_bus_async() -> EventBus:
    """Return the singleton EventBus instance (async-safe init)."""
    global _event_bus
    if _event_bus is None:
        async with _bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
    return _event_bus


def get_event_bus() -> EventBus:
    """Return the singleton EventBus instance (sync)."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the singleton (for testing)."""
    global _event_bus
    _event_bus = None


# ── SSE Generator ─────────────────────────────────────────────

async def sse_generator(
    channel: str,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from a channel.

    Automatically sends keepalive pings every _KEEPALIVE_INTERVAL seconds.
    Detects idle clients via _MAX_IDLE_SECONDS timeout.
    Unsubscribes from the channel in the ``finally`` block.
    """
    bus = get_event_bus()
    queue = await bus.subscribe(channel)
    last_event = time.monotonic()

    try:
        while True:
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=_KEEPALIVE_INTERVAL,
                )
                last_event = time.monotonic()
                yield event.to_sse()
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - last_event
                if elapsed > _MAX_IDLE_SECONDS:
                    logger.info("SSE client idle timeout on channel: %s", channel)
                    break
                yield _KEEPALIVE.to_sse()
    except asyncio.CancelledError:
        logger.debug("SSE client disconnected from channel: %s", channel)
    finally:
        await bus.unsubscribe(channel, queue)
        logger.debug("Cleaned up SSE subscription: %s", channel)
