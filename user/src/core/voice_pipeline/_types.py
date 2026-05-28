"""VoicePipeline internal types — structured results and configuration.

Design invariants:
  1. All types are dataclasses — no Pydantic, zero bloat.
  2. Fields default to empty/zero — never raise on missing data.
  3. Every result carries a `source` field for audit tracing.
  4. STT backends return TranscriptionResult — the ONLY output type.
  5. Audio format is an enum — no magic strings.
  6. INBOUND ONLY: audio → text. No TTS types exist here.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# ──────────────────────────────────────────────────────────────
#  AUDIO FORMAT
# ──────────────────────────────────────────────────────────────


class AudioFormat(str, enum.Enum):
    """Supported audio formats for the voice pipeline.

    Each format maps to a file extension used by the FormatAdapter
    for conversion routing. The canonical output format for STT
    engines is WAV (16kHz mono PCM).
    """

    OGG = "ogg"  # WhatsApp voice notes, Telegram (opus codec)
    MP3 = "mp3"  # Generic audio
    WAV = "wav"  # Canonical STT input format
    M4A = "m4a"  # Apple audio, WhatsApp audio messages
    OPUS = "opus"  # WebRTC, Telegram voice
    WEBM = "webm"  # Web audio, some recording APIs
    AMR = "amr"  # Legacy mobile audio
    AAC = "aac"  # Apple lossy
    FLAC = "flac"  # Lossless, some STT engines prefer this
    UNKNOWN = "unknown"  # Fallback for unrecognized formats

    @classmethod
    def from_mime(cls, mime_type: str) -> AudioFormat:
        """Map a MIME type to an AudioFormat.

        Common MIME types from channel providers:
          - audio/ogg → OGG
          - audio/ogg; codecs=opus → OGG
          - audio/mpeg → MP3
          - audio/mp4 → M4A
          - audio/webm → WEBM
          - audio/amr → AMR
          - audio/aac → AAC
          - audio/flac → FLAC
          - audio/wav → WAV
          - audio/x-wav → WAV
        """
        if not mime_type:
            return cls.UNKNOWN

        # Strip parameters (e.g. "; codecs=opus")
        base_mime = mime_type.split(";")[0].strip().lower()

        mapping = {
            "audio/ogg": cls.OGG,
            "audio/mpeg": cls.MP3,
            "audio/mp4": cls.M4A,
            "audio/webm": cls.WEBM,
            "audio/amr": cls.AMR,
            "audio/aac": cls.AAC,
            "audio/flac": cls.FLAC,
            "audio/wav": cls.WAV,
            "audio/x-wav": cls.WAV,
            "audio/opus": cls.OPUS,
        }
        return mapping.get(base_mime, cls.UNKNOWN)

    @classmethod
    def from_extension(cls, ext: str) -> AudioFormat:
        """Map a file extension to an AudioFormat.

        Args:
            ext: File extension with or without leading dot.
        """
        if not ext:
            return cls.UNKNOWN

        clean = ext.lstrip(".").lower()
        mapping = {
            "ogg": cls.OGG,
            "oga": cls.OGG,
            "mp3": cls.MP3,
            "wav": cls.WAV,
            "wave": cls.WAV,
            "m4a": cls.M4A,
            "mp4": cls.M4A,  # audio-only mp4
            "opus": cls.OPUS,
            "webm": cls.WEBM,
            "amr": cls.AMR,
            "aac": cls.AAC,
            "flac": cls.FLAC,
        }
        return mapping.get(clean, cls.UNKNOWN)


# ──────────────────────────────────────────────────────────────
#  TRANSCRIPTION RESULT
# ──────────────────────────────────────────────────────────────


@dataclass
class TranscriptionResult:
    """Structured output from STT transcription.

    This is the ONLY result type returned by the Ear service.
    Every STT backend must produce a TranscriptionResult.

    Invariants:
      - NEVER raises — all errors captured in `error` field.
      - `success=False` with empty `transcribed_text` is a valid
        result (audio was untranscribable or service unavailable).
      - `source` traces which backend produced the result.
    """

    success: bool = False  # Did transcription succeed?
    transcribed_text: str = ""  # STT output text
    confidence: float = 0.0  # 0.0-1.0 (backend-specific)
    language: str = ""  # Detected language code (e.g. "es", "en")
    duration_seconds: float = 0.0  # Audio duration
    audio_format: str = ""  # Original audio format
    backend: str = ""  # Which STT backend was used
    error: str = ""  # Error details if failed
    source: str = "deterministic"  # Audit source trace

    @property
    def is_empty(self) -> bool:
        """Check if transcription produced no text."""
        return not self.transcribed_text.strip()

    @property
    def text_preview(self) -> str:
        """First 200 chars of transcription for logging."""
        return self.transcribed_text[:200]


# ──────────────────────────────────────────────────────────────
#  FORMAT CONVERSION RESULT
# ──────────────────────────────────────────────────────────────


@dataclass
class ConversionResult:
    """Output from FormatAdapter audio conversion.

    Contains the converted WAV bytes and metadata about
    the original and converted audio.
    """

    success: bool = False  # Did conversion succeed?
    wav_bytes: bytes = b""  # Converted WAV audio (16kHz mono PCM)
    original_format: str = ""  # Input audio format
    original_size_bytes: int = 0  # Input file size
    converted_size_bytes: int = 0  # Output WAV file size
    duration_seconds: float = 0.0  # Audio duration
    sample_rate: int = 16000  # Output sample rate
    channels: int = 1  # Output channels (mono)
    error: str = ""  # Error details if failed
    source: str = "deterministic"  # Audit source trace


# ──────────────────────────────────────────────────────────────
#  STT BACKEND CONFIGURATION
# ──────────────────────────────────────────────────────────────


@dataclass
class STTBackendConfig:
    """Configuration for an STT backend.

    Each backend has its own config. The Ear service uses
    this to initialize the selected backend at runtime.
    """

    backend_name: str = "auto"  # auto|dummy|whisper|faster_whisper|cloud
    language: str = ""  # Hint language (empty = auto-detect)
    model_size: str = "base"  # Whisper model: tiny|base|small|medium|large
    device: str = "cpu"  # cpu|cuda for local models
    compute_type: str = "int8"  # float16|int8|int8_float16 for faster-whisper
    api_key: str = ""  # Cloud API key (if using cloud backend)
    api_base_url: str = ""  # Cloud API base URL
    timeout_seconds: float = 30.0  # STT request timeout
    max_audio_seconds: float = 600.0  # Maximum audio duration to transcribe
    fallback_chain: Sequence[str] = ()  # Override default fallback: first available wins


# ──────────────────────────────────────────────────────────────
#  VOICE PIPELINE METRICS
# ──────────────────────────────────────────────────────────────


@dataclass
class VoicePipelineMetrics:
    """Runtime metrics for the voice pipeline.

    Thread-safe — updated by the Ear service after each transcription.
    """

    total_transcriptions: int = 0
    successful_transcriptions: int = 0
    failed_transcriptions: int = 0
    total_audio_seconds: float = 0.0
    total_conversion_count: int = 0
    failed_conversions: int = 0
    backend_usage: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Transcription success rate (0.0-1.0)."""
        if self.total_transcriptions == 0:
            return 1.0
        return self.successful_transcriptions / self.total_transcriptions


# ──────────────────────────────────────────────────────────────
#  PUBLIC EXPORTS
# ──────────────────────────────────────────────────────────────

__all__ = [
    "AudioFormat",
    "ConversionResult",
    "STTBackendConfig",
    "TranscriptionResult",
    "VoicePipelineMetrics",
]
