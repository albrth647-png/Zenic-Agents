"""VoicePipeline — Audio transcription services for Zenic-Agents.

SINGLE RESPONSIBILITY: Convert inbound audio → text for the core system.

The VoicePipeline is the infrastructure layer that powers the A52
VoiceChannelAgent. It provides two independent services:

  1. Ear (STT)     — Speech-to-Text transcription
  2. FormatAdapter  — Audio format conversion (any → WAV 16kHz mono)

Design invariants:
  1. INBOUND ONLY — audio → text. No TTS exists here.
  2. The motor reads audios but responds ONLY in text.
  3. Core NEVER knows if input came as text or voice.
  4. Both services NEVER raise — errors captured in result types.
  5. Zero bloat — backends are lazy-loaded, missing deps handled.
  6. Thread-safe — safe for concurrent use.

Architecture:
  ┌──────────┐    ┌────────────────┐    ┌──────────┐
  │ Channel  │───▶│ FormatAdapter   │───▶│   Ear    │───▶ Transcribed
  │ Provider │    │ (any → WAV)     │    │  (STT)   │     Text
  └──────────┘    └────────────────┘    └──────────┘
       │                                       │
       ▼                                       ▼
  audio_bytes                            TranscriptionResult
  audio_format                           (text, confidence, lang)

Usage:
    from src.core.voice_pipeline import Ear, FormatAdapter

    # Initialize
    ear = Ear()                    # Auto-detect best STT backend
    adapter = FormatAdapter()      # Convert any format → WAV

    # Convert audio format
    conv = adapter.convert(audio_bytes, "ogg")
    if conv.success:
        # Transcribe
        result = ear.transcribe(conv.wav_bytes, "wav")
        if result.success:
            print(result.transcribed_text)
"""

from __future__ import annotations

from typing import Any

# ── Internal Types ────────────────────────────────────────────
from ._types import (
    AudioFormat,
    ConversionResult,
    STTBackendConfig,
    TranscriptionResult,
    VoicePipelineMetrics,
)

# ── Ear (STT Service) ────────────────────────────────────────
from .ear import (
    CloudBackend,
    DummyBackend,
    Ear,
    FasterWhisperBackend,
    STTBackend,
    WhisperBackend,
)

# ── FormatAdapter ────────────────────────────────────────────
from .format_adapter import (
    FormatAdapter,
    get_format_adapter,
)

# ──────────────────────────────────────────────────────────────
#  VOICE PIPELINE — UNIFIED ENTRY POINT
# ──────────────────────────────────────────────────────────────


class VoicePipeline:
    """Unified entry point for the voice → text pipeline.

    Combines FormatAdapter + Ear into a single service that
    handles the full pipeline: download → convert → transcribe.

    This is the convenience class that the A52 VoiceChannelAgent
    will use internally. It orchestrates format conversion and
    STT transcription in the correct order.

    Usage:
        pipeline = VoicePipeline()
        result = pipeline.process(audio_bytes, "ogg")
        if result.success:
            print(result.transcribed_text)
    """

    def __init__(
        self,
        stt_config: STTBackendConfig | None = None,
        *,
        format_adapter: FormatAdapter | None = None,
        ear: Ear | None = None,
    ) -> None:
        """Initialize the VoicePipeline.

        Args:
            stt_config: Configuration for the STT backend.
                        If None, auto-detects best available.
            format_adapter: Custom FormatAdapter instance.
                           If None, creates a default one.
            ear: Custom Ear instance.
                 If None, creates one with stt_config.
        """
        self._adapter = format_adapter or FormatAdapter()
        self._ear = ear or Ear(config=stt_config)

    def process(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Full pipeline: convert → transcribe.

        Steps:
          1. Convert audio to WAV 16kHz mono (if needed)
          2. Transcribe the WAV audio via STT
          3. Return TranscriptionResult

        If the input is already WAV 16kHz mono, step 1 is a
        lightweight pass-through (pydub re-encodes but the format
        is already correct).

        NEVER raises — returns TranscriptionResult.

        Args:
            audio_bytes: Raw audio data in any supported format.
            audio_format: Hint about the audio format.
            language: Hint about the spoken language.

        Returns:
            TranscriptionResult with transcription text or error.
        """
        if not audio_bytes:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                error="Empty audio bytes — nothing to process",
                source="voice_pipeline",
            )

        # Step 1: Convert to WAV if adapter is available
        if self._adapter.is_available:
            # Only convert if not already WAV 16kHz mono
            needs_conversion = audio_format.lower().strip().lstrip(".") not in ("wav", "x-wav", "wave", "")

            if needs_conversion:
                conv = self._adapter.convert(audio_bytes, audio_format)
                if not conv.success:
                    return TranscriptionResult(
                        success=False,
                        audio_format=audio_format,
                        error=f"Format conversion failed: {conv.error}",
                        source="voice_pipeline",
                    )
                stt_input = conv.wav_bytes
                stt_format = "wav"
            else:
                stt_input = audio_bytes
                stt_format = audio_format
        else:
            # No adapter — try STT directly (it may handle the format)
            stt_input = audio_bytes
            stt_format = audio_format

        # Step 2: Transcribe
        result = self._ear.transcribe(stt_input, stt_format, language)

        # Enrich result with original format info
        if not result.audio_format:
            result.audio_format = audio_format

        return result

    async def process_async(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Async version of process().

        Runs the full pipeline in a thread pool.
        """
        import asyncio

        return await asyncio.to_thread(
            self.process,
            audio_bytes,
            audio_format,
            language,
        )

    # ── Delegate Properties ───────────────────────────────────

    @property
    def ear(self) -> Ear:
        """Access the underlying Ear STT service."""
        return self._ear

    @property
    def adapter(self) -> FormatAdapter:
        """Access the underlying FormatAdapter."""
        return self._adapter

    @property
    def active_backend(self) -> str:
        """Name of the active STT backend."""
        return self._ear.active_backend

    @property
    def available_backends(self) -> list[str]:
        """Names of all available STT backends."""
        return self._ear.available_backends

    def health_check(self) -> dict[str, Any]:
        """Full health check of the VoicePipeline."""
        return {
            "service": "voice_pipeline",
            "format_adapter": self._adapter.health_check(),
            "ear": self._ear.health_check(),
        }


# ──────────────────────────────────────────────────────────────
#  PUBLIC EXPORTS
# ──────────────────────────────────────────────────────────────

__all__ = [
    # Types
    "AudioFormat",
    "CloudBackend",
    "ConversionResult",
    "DummyBackend",
    "Ear",
    "FasterWhisperBackend",
    # FormatAdapter
    "FormatAdapter",
    # Ear (STT)
    "STTBackend",
    "STTBackendConfig",
    "TranscriptionResult",
    # Unified Pipeline
    "VoicePipeline",
    "VoicePipelineMetrics",
    "WhisperBackend",
    "get_format_adapter",
]
