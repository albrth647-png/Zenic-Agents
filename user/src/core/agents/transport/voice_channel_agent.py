"""A52 VoiceChannelAgent — SINGLE RESPONSIBILITY: Convert inbound audio → text.

Deterministic voice transcription pipeline:
  download → validate → convert → transcribe → deliver text

This agent is NOT a chatbot. It does not generate content.
It converts inbound voice/audio messages into text so the core
system can process them identically to text messages.

Design invariants:
  1. execute() NEVER raises — all errors captured in VoiceChannelResult.
  2. INBOUND ONLY — audio → text. The motor NEVER responds in audio.
  3. Core system NEVER knows if input came as text or voice.
  4. Every transcription is audited via BaseAgent.run() resilience wrapper.
  5. If VoicePipeline is not wired, returns safe fallback result.
  6. Deterministic by design — VoicePipeline handles STT backend selection.
  7. Thread-safe — VoicePipeline and channel providers have their own locks.

User constraint (verbatim):
  "quiero solo que mi motor responda y lea audios pero responda en
   texto Nono en audio"
  → Motor READS audios, responds ONLY in text. No TTS. No outbound audio.

Pipeline:
  ┌───────────────┐    ┌───────────┐    ┌──────────────┐    ┌─────────┐
  │ 1. Download    │───▶│ 2. Validate│───▶│ 3. Convert   │───▶│ 4. STT  │───▶ Text
  │   audio bytes  │    │   limits   │    │   → WAV 16k  │    │ Ear     │
  └───────────────┘    └───────────┘    └──────────────┘    └─────────┘
       ▲                                                           │
       │                                                           ▼
  Channel Provider                                    VoiceChannelResult
  (download_media)                                    (transcribed_text)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import time
from typing import Any

from ..resilience import BaseAgent
from ..schemas.types._transport_types import VoiceChannelInput, VoiceChannelResult

# ──────────────────────────────────────────────────────────────
#  LAZY IMPORTS — avoid circular dependency at module level
# ──────────────────────────────────────────────────────────────

_logger = logging.getLogger("zenic_agents.agents.transport.voice_channel")

# Module-level references (resolved on first use)
_voice_pipeline_cls = None  # VoicePipeline
_stt_config_cls = None  # STTBackendConfig
_audio_format_cls = None  # AudioFormat
_transcription_result_cls = None  # TranscriptionResult
_can_receive_voice_fn = None  # can_receive_voice
_platform_limits_cls = None  # PlatformLimits


def _resolve_deps() -> None:
    """Resolve voice pipeline dependencies lazily (once).

    This avoids circular imports at module load time while keeping
    the agent fully wired to the voice pipeline infrastructure at runtime.
    """
    global _voice_pipeline_cls, _stt_config_cls, _audio_format_cls
    global _transcription_result_cls, _can_receive_voice_fn, _platform_limits_cls

    if _voice_pipeline_cls is not None:
        return  # Already resolved

    from src.core.channels._formatter._limits import PlatformLimits as _PL
    from src.core.channels._protocol import can_receive_voice as _crv
    from src.core.voice_pipeline import VoicePipeline as _VP
    from src.core.voice_pipeline._types import (
        AudioFormat as _AF,
    )
    from src.core.voice_pipeline._types import (
        STTBackendConfig as _SBC,
    )
    from src.core.voice_pipeline._types import (
        TranscriptionResult as _TR,
    )

    _voice_pipeline_cls = _VP
    _stt_config_cls = _SBC
    _audio_format_cls = _AF
    _transcription_result_cls = _TR
    _can_receive_voice_fn = _crv
    _platform_limits_cls = _PL


# ──────────────────────────────────────────────────────────────
#  ASYNC BRIDGE
# ──────────────────────────────────────────────────────────────


def _run_async(coro: Any, timeout: float = 60.0) -> Any:
    """Bridge an async coroutine to synchronous execution.

    Handles two cases:
      1. No event loop running → asyncio.run()
      2. Event loop already running → ThreadPoolExecutor with new loop

    Voice operations may take longer than text (large audio files),
    so the default timeout is 60 seconds.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=timeout)


# ──────────────────────────────────────────────────────────────
#  AUDIO DOWNLOAD HELPERS
# ──────────────────────────────────────────────────────────────


async def _download_from_provider(
    provider: Any,
    media_id: str,
) -> bytes | None:
    """Download audio bytes from a channel provider.

    Uses the provider's download_media() method (WhatsApp) or
    falls back to URL-based download for other providers.

    Args:
        provider: Channel provider with download_media capability.
        media_id: Media ID or URL from the inbound message.

    Returns:
        Raw audio bytes, or None on failure.
    """
    try:
        # Try provider's download_media first (WhatsApp pattern)
        if hasattr(provider, "download_media") and callable(provider.download_media):
            return await provider.download_media(media_id)

        # Try direct URL download
        if media_id.startswith(("http://", "https://")):
            return await _download_url(media_id)

        return None
    except Exception as e:
        _logger.error("Audio download failed: %s", e)
        return None


async def _download_url(url: str) -> bytes | None:
    """Download audio from a direct URL.

    Uses aiohttp if available, falls back to urllib.
    """
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    return await resp.read()
                _logger.error("URL download failed: HTTP %d", resp.status)
                return None
    except ImportError:
        pass

    # Fallback to urllib
    try:
        import urllib.request

        def _sync_download() -> bytes | None:
            req = urllib.request.Request(url)  # noqa: S310
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                return resp.read()

        return await asyncio.to_thread(_sync_download)
    except Exception as e:
        _logger.error("URL download fallback failed: %s", e)
        return None


def _read_local_file(path: str) -> bytes | None:
    """Read audio bytes from a local filesystem path.

    Args:
        path: Absolute or relative path to the audio file.

    Returns:
        Raw audio bytes, or None on failure.
    """
    try:
        if not os.path.isfile(path):
            _logger.error("Audio file not found: %s", path)
            return None

        # Safety: limit file size
        size = os.path.getsize(path)
        max_size = 50 * 1024 * 1024  # 50 MB
        if size > max_size:
            _logger.error(
                "Audio file too large: %d bytes (max %d)",
                size,
                max_size,
            )
            return None

        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        _logger.error("Failed to read audio file '%s': %s", path, e)
        return None


# ──────────────────────────────────────────────────────────────
#  AUDIO LIMIT VALIDATION
# ──────────────────────────────────────────────────────────────


def _get_voice_duration_limit(channel: str) -> int:
    """Get the maximum audio duration (seconds) for a channel.

    Uses PlatformLimits when available, defaults to 600s.
    """
    if _platform_limits_cls is None:
        return 600

    limits = _platform_limits_cls()
    attr = f"{channel}_voice_max_duration"
    return getattr(limits, attr, 600)


def _get_voice_size_limit(channel: str) -> int:
    """Get the maximum audio file size (bytes) for a channel.

    Uses PlatformLimits when available, defaults to 16MB.
    """
    if _platform_limits_cls is None:
        return 16 * 1024 * 1024

    limits = _platform_limits_cls()
    attr = f"{channel}_voice_max_size"
    return getattr(limits, attr, 16 * 1024 * 1024)


# ──────────────────────────────────────────────────────────────
#  A52 VOICE CHANNEL AGENT
# ──────────────────────────────────────────────────────────────


class VoiceChannelAgent(BaseAgent[VoiceChannelResult]):
    """A52: Deterministic voice transcription agent.

    Single Responsibility: Convert inbound audio → text.
    Pipeline: download → validate → convert → transcribe → deliver text

    This agent is the ONLY way audio enters the core system.
    It ensures every inbound audio message is:
      - Downloaded from the channel provider (WhatsApp, Telegram, etc.)
      - Validated against platform limits (size, duration)
      - Converted to WAV 16kHz mono PCM (canonical STT format)
      - Transcribed via the VoicePipeline (Ear STT service)
      - Delivered as plain text — the core NEVER sees audio

    The core system receives text and processes it identically
    regardless of whether it came from a text message or a voice
    message. This is the fundamental design invariant.

    IMPORTANT: The motor reads audios but responds ONLY in text.
    No TTS. No outbound audio. Ever.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(name="A52_VoiceChannelAgent", **kwargs)
        self._voice_pipeline: Any | None = None  # VoicePipeline — wired at startup
        self._registry: Any | None = None  # AdapterRegistry — wired at startup

    # ── Dependency Wiring ─────────────────────────────────────

    def wire(
        self,
        voice_pipeline: Any,  # VoicePipeline
        registry: Any = None,  # AdapterRegistry (for provider download)
    ) -> None:
        """Wire voice pipeline and channel infrastructure dependencies.

        Called during system startup by the orchestrator.
        The voice_pipeline is REQUIRED for transcription.
        The registry is optional but needed for downloading
        audio from channel providers (e.g. WhatsApp media API).

        Args:
            voice_pipeline: VoicePipeline instance for STT transcription.
            registry: AdapterRegistry instance for provider access.
        """
        _resolve_deps()
        self._voice_pipeline = voice_pipeline
        self._registry = registry
        _logger.info(
            "A52 wired: voice_pipeline=%s, registry=%s",
            type(voice_pipeline).__name__ if voice_pipeline else None,
            type(registry).__name__ if registry else None,
        )

    # ── Input Validation ──────────────────────────────────────

    def _validate_input(self, input_data: Any) -> VoiceChannelInput:
        """Normalize input to VoiceChannelInput.

        Accepts:
          - VoiceChannelInput instance (preferred)
          - dict with audio_url/audio_path/channel keys (convenience)
          - ChannelMessage with voice_url (from webhook parsing)
        """
        if isinstance(input_data, VoiceChannelInput):
            return input_data

        if isinstance(input_data, dict):
            return VoiceChannelInput(
                audio_url=input_data.get("audio_url", ""),
                audio_path=input_data.get("audio_path", ""),
                audio_format=input_data.get("audio_format", ""),
                channel=input_data.get("channel", ""),
                sender=input_data.get("sender", ""),
                duration_seconds=input_data.get("duration_seconds", 0.0),
                metadata=input_data.get("metadata", {}),
            )

        # Try to extract from ChannelMessage-like objects
        voice_url = getattr(input_data, "voice_url", "")
        if voice_url:
            return VoiceChannelInput(
                audio_url=voice_url,
                audio_format=getattr(input_data, "voice_format", ""),
                channel=getattr(input_data, "recipient", ""),
                sender="",
                duration_seconds=getattr(input_data, "voice_duration", 0.0),
                metadata=getattr(input_data, "metadata", {}),
            )

        # Fallback for unknown types
        return VoiceChannelInput(
            audio_url=str(input_data) if input_data else "",
        )

    # ── Core Execution ────────────────────────────────────────

    def execute(self, input_data: Any) -> VoiceChannelResult:
        """Execute the voice transcription pipeline synchronously.

        Bridges to async internally. NEVER raises.
        All errors are captured in the returned VoiceChannelResult.
        """
        data = self._validate_input(input_data)
        _resolve_deps()

        # Fast path: no voice pipeline wired → fallback result
        if self._voice_pipeline is None:
            _logger.warning("A52: voice pipeline not wired — returning fallback result")
            return self._make_result(
                data=data,
                success=False,
                error="VoicePipeline not wired — call wire() before execute()",
                source="deterministic",
            )

        # Validate: at least one audio source
        if not data.audio_url and not data.audio_path:
            return self._make_result(
                data=data,
                success=False,
                error="No audio source provided — need audio_url or audio_path",
                source="deterministic",
            )

        try:
            return _run_async(self._transcribe(data))
        except concurrent.futures.TimeoutError:
            return self._make_result(
                data=data,
                success=False,
                error="Transcription timed out",
                source="deterministic",
            )
        except Exception as e:
            return self._make_result(
                data=data,
                success=False,
                error=f"Transcription failed: {e}",
                source="deterministic",
            )

    async def _transcribe(self, data: VoiceChannelInput) -> VoiceChannelResult:
        """Core async transcription pipeline.

        Steps:
          1. Download audio bytes (from URL, path, or channel provider)
          2. Validate audio against platform limits
          3. Convert audio format via VoicePipeline (→ WAV 16kHz mono)
          4. Transcribe via VoicePipeline (→ text)
          5. Return VoiceChannelResult with transcribed text
        """
        start = time.monotonic()

        # ── Step 1: Download audio bytes ──
        audio_bytes: bytes | None = None

        if data.audio_path:
            # Local file path
            audio_bytes = await asyncio.to_thread(_read_local_file, data.audio_path)
            if audio_bytes is None:
                return self._make_result(
                    data=data,
                    success=False,
                    error=f"Cannot read audio file: {data.audio_path}",
                )
            _logger.info(
                "A52: loaded audio from path (%d bytes)",
                len(audio_bytes),
            )

        elif data.audio_url:
            # URL or media ID — try provider download first
            audio_bytes = await self._download_audio(data)

            if audio_bytes is None:
                return self._make_result(
                    data=data,
                    success=False,
                    error=f"Cannot download audio from: {data.audio_url[:100]}",
                )
            _logger.info(
                "A52: downloaded audio (%d bytes)",
                len(audio_bytes),
            )

        if not audio_bytes:
            return self._make_result(
                data=data,
                success=False,
                error="No audio bytes obtained — download/read failed",
            )

        # ── Step 2: Validate against platform limits ──
        channel = data.channel or "whatsapp"  # Default to WhatsApp limits
        size_limit = _get_voice_size_limit(channel)
        _get_voice_duration_limit(channel)

        if len(audio_bytes) > size_limit:
            return self._make_result(
                data=data,
                success=False,
                error=f"Audio too large: {len(audio_bytes)} bytes " f"(limit: {size_limit} bytes for {channel})",
            )

        # ── Step 3 + 4: Convert → Transcribe via VoicePipeline ──
        language = data.metadata.get("language", "")

        # Use VoicePipeline.process() which handles convert → transcribe
        transcription = self._voice_pipeline.process(
            audio_bytes=audio_bytes,
            audio_format=data.audio_format,
            language=language,
        )

        # ── Step 5: Build result ──
        elapsed = time.monotonic() - start

        if transcription.success:
            _logger.info(
                "A52: transcription succeeded in %.2fs " "(text_len=%d, lang=%s, backend=%s)",
                elapsed,
                len(transcription.transcribed_text),
                transcription.language,
                transcription.backend,
            )
        else:
            _logger.warning(
                "A52: transcription failed in %.2fs (backend=%s): %s",
                elapsed,
                transcription.backend,
                transcription.error[:200] if transcription.error else "(no error)",
            )

        return VoiceChannelResult(
            success=transcription.success,
            transcribed_text=transcription.transcribed_text,
            channel=data.channel,
            audio_format=data.audio_format or transcription.audio_format,
            duration_seconds=transcription.duration_seconds or data.duration_seconds,
            confidence=transcription.confidence,
            language=transcription.language,
            error=transcription.error,
            source=transcription.source,
        )

    # ── Audio Download ────────────────────────────────────────

    async def _download_audio(self, data: VoiceChannelInput) -> bytes | None:
        """Download audio bytes from URL or channel provider.

        Tries in order:
          1. Channel provider's download_media() (if registry has provider)
          2. Direct URL download (aiohttp / urllib)

        Args:
            data: VoiceChannelInput with audio_url.

        Returns:
            Raw audio bytes, or None on failure.
        """
        audio_url = data.audio_url

        # Try channel provider download (WhatsApp pattern)
        if self._registry and data.channel:
            try:
                # Get the provider for this channel
                provider = self._registry.get_provider(data.channel)
                if provider is not None:
                    # Check voice capability
                    if _can_receive_voice_fn and _can_receive_voice_fn(provider):
                        result = await _download_from_provider(provider, audio_url)
                        if result is not None:
                            return result
            except Exception as e:
                _logger.debug(
                    "A52: provider download failed for %s: %s",
                    data.channel,
                    e,
                )

        # Direct URL download
        if audio_url.startswith(("http://", "https://")):
            return await _download_url(audio_url)

        # audio_url might be a media ID without a provider match
        _logger.warning(
            "A52: cannot download audio (url=%s, channel=%s, registry=%s)",
            audio_url[:50] if audio_url else "(empty)",
            data.channel,
            "wired" if self._registry else "NOT wired",
        )
        return None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _make_result(
        data: VoiceChannelInput,
        success: bool = False,
        transcribed_text: str = "",
        confidence: float = 0.0,
        language: str = "",
        error: str = "",
        source: str = "deterministic",
    ) -> VoiceChannelResult:
        """Build a VoiceChannelResult with sensible defaults."""
        return VoiceChannelResult(
            success=success,
            transcribed_text=transcribed_text,
            channel=data.channel,
            audio_format=data.audio_format,
            duration_seconds=data.duration_seconds,
            confidence=confidence,
            language=language,
            error=error,
            source=source,
        )

    # ── Fallback ──────────────────────────────────────────────

    def fallback(self, input_data: Any) -> VoiceChannelResult:
        """Deterministic fallback when execute() fails.

        Returns a safe result indicating transcription was not attempted.
        The audio reference is logged for later retry.
        """
        data = self._validate_input(input_data)
        _logger.info(
            "A52 fallback: audio_url=%s, channel=%s",
            data.audio_url[:50] if data.audio_url else "(none)",
            data.channel or "(none)",
        )
        return VoiceChannelResult(
            success=False,
            transcribed_text="",
            channel=data.channel,
            audio_format=data.audio_format,
            duration_seconds=data.duration_seconds,
            confidence=0.0,
            language="",
            error="Agent fallback — transcription not attempted",
            source="fallback",
        )

    # ── Async Entry Point ─────────────────────────────────────

    async def transcribe(self, input_data: Any) -> VoiceChannelResult:
        """Async entry point for direct async callers.

        Use this when calling from an async context to avoid
        the sync-async bridge overhead. This is the preferred
        entry point for async orchestrators.

        Args:
            input_data: VoiceChannelInput, dict, or ChannelMessage with voice_url.

        Returns:
            VoiceChannelResult with transcription outcome.
        """
        data = self._validate_input(input_data)
        _resolve_deps()

        if self._voice_pipeline is None:
            return self._make_result(
                data=data,
                success=False,
                error="VoicePipeline not wired — call wire() before transcribe()",
            )

        if not data.audio_url and not data.audio_path:
            return self._make_result(
                data=data,
                success=False,
                error="No audio source provided",
            )

        try:
            return await self._transcribe(data)
        except Exception as e:
            return self._make_result(
                data=data,
                success=False,
                error=f"Async transcription failed: {e}",
            )

    # ── Status ────────────────────────────────────────────────

    @property
    def is_wired(self) -> bool:
        """Whether the agent has its dependencies wired."""
        return self._voice_pipeline is not None

    @property
    def stt_backend(self) -> str:
        """Name of the active STT backend (via VoicePipeline)."""
        if self._voice_pipeline is not None:
            return self._voice_pipeline.active_backend
        return "not_wired"

    def health_check(self) -> dict[str, Any]:
        """VoiceChannelAgent health check."""
        return {
            "agent": "A52_VoiceChannelAgent",
            "wired": self.is_wired,
            "stt_backend": self.stt_backend,
            "registry_wired": self._registry is not None,
            "voice_pipeline_health": (
                self._voice_pipeline.health_check() if self._voice_pipeline is not None else None
            ),
        }


# ──────────────────────────────────────────────────────────────
#  PUBLIC EXPORTS
# ──────────────────────────────────────────────────────────────

__all__ = ["VoiceChannelAgent"]
