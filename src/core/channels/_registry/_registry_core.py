"""
ZENIC-AGENTS — Adapter Registry

Dynamic registry for channel providers, mirroring the ExecutorRegistry pattern.
Manages provider registration, lookup, lifecycle (start/stop), and
fallback-based message delivery.

Design invariants:
  1. Thread-safe — all mutations use RLock.
  2. Never raises on send — always returns ChannelResponse.
  3. 'log' provider is always registered as terminal fallback.
  4. Provider registration is idempotent.
  5. send_with_fallback() never fails — at minimum, logs the message.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .._protocol import ChannelProvider, InboundChannelProvider
from .._types import (
    ChannelCapability,
    ChannelMessage,
    ChannelResponse,
    ConfirmationHandler,
    ConfirmationRequest,
    DeliveryStatus,
    MessageHandler,
)

logger = logging.getLogger("zenic_agents.channels.registry")


class AdapterRegistry:
    """Central registry for all channel providers.

    Pattern: mirrors ExecutorRegistry — string-keyed, dynamic registration,
    singleton access, safety integration.

    Features:
      - Register/unregister providers by name
      - Alias support (multiple names → same provider)
      - Fallback routing: try primary → fallback chain → log
      - Inbound provider lifecycle management
      - Thread-safe
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: dict[str, ChannelProvider] = {}
        self._inbound_providers: dict[str, InboundChannelProvider] = {}
        self._fallback_map: dict[str, list[str]] = {}  # channel → [fallback_chain]
        self._stats = {
            "total_sent": 0,
            "total_sent_success": 0,
            "total_sent_failed": 0,
            "total_fallback_used": 0,
        }

    # ── Registration ────────────────────────────────────────────

    def register(
        self,
        provider: ChannelProvider,
        aliases: list[str] | None = None,
    ) -> None:
        """Register a channel provider.

        Args:
            provider: The ChannelProvider instance.
            aliases: Optional alternative names for the same provider.
        """
        with self._lock:
            name = provider.name
            self._providers[name] = provider

            if isinstance(provider, InboundChannelProvider):
                self._inbound_providers[name] = provider

            if aliases:
                for alias in aliases:
                    self._providers[alias] = provider
                    if isinstance(provider, InboundChannelProvider):
                        self._inbound_providers[alias] = provider

            logger.debug(
                "AdapterRegistry: registered provider '%s' (aliases=%s)",
                name,
                aliases,
            )

    def unregister(self, name: str) -> bool:
        """Unregister a provider by name.

        Returns:
            True if found and removed, False otherwise.
        """
        with self._lock:
            provider = self._providers.pop(name, None)
            self._inbound_providers.pop(name, None)

            if provider is None:
                return False

            # Also remove aliases pointing to the same provider
            to_remove = [k for k, v in self._providers.items() if v is provider and k != name]
            for k in to_remove:
                del self._providers[k]
                self._inbound_providers.pop(k, None)

            logger.info("AdapterRegistry: unregistered provider '%s'", name)
            return True

    def get(self, name: str) -> ChannelProvider | None:
        """Get a provider by name."""
        with self._lock:
            return self._providers.get(name)

    # ── Fallback Configuration ──────────────────────────────────

    def set_fallback_chain(self, channel: str, fallbacks: list[str]) -> None:
        """Set the fallback chain for a channel.

        When send_with_fallback() is called and the primary channel fails,
        it tries each fallback in order until one succeeds.
        The 'log' provider should always be the terminal fallback.

        Args:
            channel: Primary channel name.
            fallbacks: Ordered list of fallback channel names.
        """
        with self._lock:
            self._fallback_map[channel] = fallbacks
            logger.debug(
                "AdapterRegistry: set fallback for '%s' → %s",
                channel,
                fallbacks,
            )

    def get_fallback_chain(self, channel: str) -> list[str]:
        """Get the fallback chain for a channel."""
        with self._lock:
            return list(self._fallback_map.get(channel, []))

    # ── Send ────────────────────────────────────────────────────

    async def send(
        self,
        channel: str,
        message: ChannelMessage,
    ) -> ChannelResponse:
        """Send a message through a specific channel.

        If the channel is not available, returns a failed ChannelResponse.
        NEVER raises.

        Args:
            channel: Provider name to send through.
            message: Universal message envelope.

        Returns:
            ChannelResponse with delivery result.
        """
        with self._lock:
            self._stats["total_sent"] += 1

        provider = self.get(channel)
        if provider is None:
            logger.warning("AdapterRegistry: no provider for channel '%s'", channel)
            return ChannelResponse(
                success=False,
                channel=channel,
                status=DeliveryStatus.FAILED,
                error=f"No provider registered for channel '{channel}'",
                timestamp=time.time(),
            )

        if not provider.is_available:
            logger.warning("AdapterRegistry: provider '%s' is not available", channel)
            return ChannelResponse(
                success=False,
                channel=channel,
                status=DeliveryStatus.FAILED,
                error=f"Provider '{channel}' is not available",
                timestamp=time.time(),
            )

        try:
            response = await provider.send(message)
            with self._lock:
                if response.success:
                    self._stats["total_sent_success"] += 1
                else:
                    self._stats["total_sent_failed"] += 1
            return response
        except Exception as e:
            logger.error(
                "AdapterRegistry: error sending via '%s': %s",
                channel,
                e,
            )
            with self._lock:
                self._stats["total_sent_failed"] += 1
            return ChannelResponse(
                success=False,
                channel=channel,
                status=DeliveryStatus.FAILED,
                error=f"Provider error: {e}",
                timestamp=time.time(),
            )

    async def send_with_fallback(
        self,
        channel: str,
        message: ChannelMessage,
        exclude_channels: set[str] | None = None,
    ) -> ChannelResponse:
        """Send a message with automatic fallback chain.

        Tries the primary channel, then each fallback in order.
        Always succeeds at minimum via the 'log' provider.

        Args:
            channel: Primary provider name.
            message: Universal message envelope.
            exclude_channels: Channels to skip (e.g., if they just failed).

        Returns:
            ChannelResponse from the first successful delivery,
            or from the last attempted channel.
        """
        exclude = exclude_channels or set()
        chain = [channel] + self.get_fallback_chain(channel)

        last_response: ChannelResponse | None = None

        for ch in chain:
            if ch in exclude:
                continue

            provider = self.get(ch)
            if provider is None or not provider.is_available:
                continue

            response = await self.send(ch, message)
            last_response = response

            if response.success:
                if ch != channel:
                    with self._lock:
                        self._stats["total_fallback_used"] += 1
                    # Mark as fallback delivery
                    return ChannelResponse(
                        success=True,
                        channel=response.channel,
                        message_id=response.message_id,
                        status=DeliveryStatus.FALLBACK,
                        metadata={
                            **response.metadata,
                            "original_channel": channel,
                            "fallback_channel": ch,
                        },
                        timestamp=response.timestamp,
                    )
                return response

        # All fallbacks failed — try log as terminal fallback
        if "log" not in exclude:
            log_provider = self.get("log")
            if log_provider and log_provider.is_available:
                response = await self.send("log", message)
                with self._lock:
                    self._stats["total_fallback_used"] += 1
                return ChannelResponse(
                    success=True,
                    channel="log",
                    status=DeliveryStatus.FALLBACK,
                    metadata={"original_channel": channel, "fallback_channel": "log"},
                    timestamp=time.time(),
                )

        # Absolute failure (shouldn't happen if log is registered)
        return last_response or ChannelResponse(
            success=False,
            channel=channel,
            status=DeliveryStatus.FAILED,
            error="All channels failed, including fallbacks",
            timestamp=time.time(),
        )

    async def send_confirmation(
        self,
        channel: str,
        request: ConfirmationRequest,
    ) -> ChannelResponse:
        """Send a confirmation request through a specific channel.

        Falls back to plain text if the channel doesn't support confirmations.

        Args:
            channel: Provider name.
            request: Confirmation request.

        Returns:
            ChannelResponse with the sent message ID.
        """
        provider = self.get(channel)
        if provider is None:
            return ChannelResponse(
                success=False,
                channel=channel,
                status=DeliveryStatus.FAILED,
                error=f"No provider for channel '{channel}'",
                timestamp=time.time(),
            )

        try:
            return await provider.send_confirmation(request)
        except Exception as e:
            logger.error(
                "AdapterRegistry: error sending confirmation via '%s': %s",
                channel,
                e,
            )
            return ChannelResponse(
                success=False,
                channel=channel,
                status=DeliveryStatus.FAILED,
                error=f"Confirmation error: {e}",
                timestamp=time.time(),
            )

    # ── Inbound Lifecycle ───────────────────────────────────────

    def set_message_handler(
        self,
        channel: str,
        handler: MessageHandler,
    ) -> bool:
        """Register an inbound message handler for a bidirectional provider.

        Returns:
            True if the provider exists and supports inbound, False otherwise.
        """
        with self._lock:
            provider = self._inbound_providers.get(channel)
            if provider is None:
                logger.warning(
                    "AdapterRegistry: no inbound provider for '%s'",
                    channel,
                )
                return False
            provider.set_message_handler(handler)
            return True

    def set_confirmation_handler(
        self,
        channel: str,
        handler: ConfirmationHandler,
    ) -> bool:
        """Register an inbound confirmation handler for a bidirectional provider.

        Returns:
            True if the provider exists and supports inbound, False otherwise.
        """
        with self._lock:
            provider = self._inbound_providers.get(channel)
            if provider is None:
                logger.warning(
                    "AdapterRegistry: no inbound provider for '%s'",
                    channel,
                )
                return False
            provider.set_confirmation_handler(handler)
            return True

    async def start_inbound(self, channel: str = "") -> None:
        """Start listening for inbound messages.

        Args:
            channel: If provided, start only this provider.
                     If empty, start all inbound providers.
        """
        with self._lock:
            providers = (
                {channel: self._inbound_providers[channel]}
                if channel and channel in self._inbound_providers
                else dict(self._inbound_providers)
            )

        for name, provider in providers.items():
            try:
                await provider.start()
                logger.info("AdapterRegistry: started inbound provider '%s'", name)
            except Exception as e:
                logger.error(
                    "AdapterRegistry: failed to start '%s': %s",
                    name,
                    e,
                )

    async def stop_all(self) -> None:
        """Stop all providers (inbound and outbound)."""
        with self._lock:
            providers = list(self._providers.values())

        # Deduplicate (aliases point to same instance)
        seen: set[int] = set()
        unique_providers: list[ChannelProvider] = []
        for p in providers:
            if id(p) not in seen:
                seen.add(id(p))
                unique_providers.append(p)

        for provider in unique_providers:
            try:
                await provider.stop()
            except Exception as e:
                logger.error(
                    "AdapterRegistry: error stopping '%s': %s",
                    provider.name,
                    e,
                )

    # ── Query ───────────────────────────────────────────────────

    def list_providers(self) -> dict[str, dict[str, Any]]:
        """List all registered providers with their status."""
        with self._lock:
            result: dict[str, dict[str, Any]] = {}
            seen: set[int] = set()
            for name, provider in self._providers.items():
                if id(provider) in seen:
                    continue
                seen.add(id(provider))
                result[name] = {
                    "available": provider.is_available,
                    "capabilities": [c.value for c in provider.capabilities],
                    "is_inbound": isinstance(provider, InboundChannelProvider),
                    "stats": provider.stats,
                }
            return result

    def get_providers_by_capability(
        self,
        capability: ChannelCapability,
    ) -> list[ChannelProvider]:
        """Get all providers that support a specific capability."""
        with self._lock:
            seen: set[int] = set()
            result: list[ChannelProvider] = []
            for provider in self._providers.values():
                if id(provider) not in seen and capability in provider.capabilities:
                    seen.add(id(provider))
                    result.append(provider)
            return result

    def get_voice_capable_providers(self) -> list[ChannelProvider]:
        """Get all providers that can receive voice/audio messages.

        Convenience method for the voice pipeline to discover
        which providers support RECEIVE_VOICE capability.

        Returns:
            List of providers with RECEIVE_VOICE capability.
        """
        return self.get_providers_by_capability(ChannelCapability.RECEIVE_VOICE)

    def get_provider_for_channel(
        self,
        channel: str,
    ) -> ChannelProvider | None:
        """Get a provider by channel name, with inbound fallback.

        If the exact channel name is not found, tries to find
        any inbound provider for that channel type.

        Args:
            channel: Channel name (e.g. "whatsapp", "telegram").

        Returns:
            ChannelProvider if found, None otherwise.
        """
        return self.get(channel)

    @property
    def registered_channels(self) -> list[str]:
        """List of unique registered channel names."""
        with self._lock:
            seen: set[int] = set()
            names: list[str] = []
            for name, provider in self._providers.items():
                if id(provider) not in seen:
                    seen.add(id(provider))
                    names.append(name)
            return names

    @property
    def stats(self) -> dict[str, Any]:
        """Registry statistics."""
        with self._lock:
            return {
                **self._stats,
                "registered_channels": len(self.registered_channels),
                "inbound_channels": len(self._inbound_providers),
                "fallback_chains": len(self._fallback_map),
            }


# ──────────────────────────────────────────────────────────────
#  SINGLETON
# ──────────────────────────────────────────────────────────────

_default_registry: AdapterRegistry | None = None
_registry_lock = threading.Lock()


def get_default_registry() -> AdapterRegistry:
    """Get the singleton AdapterRegistry instance."""
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = AdapterRegistry()
                # Register the log provider as terminal fallback
                from .._log_provider import LogChannelProvider

                _default_registry.register(LogChannelProvider())
    return _default_registry


def reset_default_registry() -> None:
    """Reset the singleton (for testing)."""
    global _default_registry
    with _registry_lock:
        _default_registry = None
