"""FormatAdapter — Audio format conversion for VoicePipeline.

SINGLE RESPONSIBILITY: Convert audio from any supported format
to WAV 16kHz mono PCM — the canonical input format for STT engines.

Design invariants:
  1. NEVER raises — all errors captured in ConversionResult.
  2. Output is ALWAYS WAV 16kHz mono PCM (standard for STT).
  3. Uses pydub + ffmpeg — lightweight, powerful, already installed.
  4. Validates audio against PlatformLimits (size, duration).
  5. Thread-safe — safe for concurrent conversions.
  6. Zero bloat — pydub is the only heavy dependency.
  7. Handles corrupt files, empty data, and unknown formats gracefully.

Supported input formats:
  ogg, mp3, wav, m4a, opus, webm, amr, aac, flac

Output format:
  WAV (PCM signed 16-bit little-endian, 16000 Hz, mono)

Usage:
    adapter = FormatAdapter()
    result = adapter.convert(audio_bytes, "ogg")
    if result.success:
        wav_data = result.wav_bytes  # Ready for STT
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional, Set

from ._types import AudioFormat, ConversionResult

_logger = logging.getLogger("zenic_agents.voice_pipeline.format_adapter")


# ──────────────────────────────────────────────────────────────
#  CANONICAL OUTPUT SPECIFICATION
# ──────────────────────────────────────────────────────────────

_CANONICAL_SAMPLE_RATE = 16000   # 16kHz — standard for STT engines
_CANONICAL_CHANNELS = 1          # Mono
_CANONICAL_SAMPLE_WIDTH = 2      # 16-bit = 2 bytes per sample
_CANONICAL_FORMAT = "wav"


# ──────────────────────────────────────────────────────────────
#  FORMAT VALIDATION
# ──────────────────────────────────────────────────────────────

# Formats supported by pydub/ffmpeg for reading
_SUPPORTED_INPUT_FORMATS: Set[str] = {
    "ogg", "mp3", "wav", "m4a", "opus", "webm",
    "amr", "aac", "flac", "oga", "mp4",
}

# Maximum reasonable audio sizes (safety limits)
_MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB — hard ceiling
_MAX_AUDIO_DURATION_SECONDS = 3600.0       # 1 hour — hard ceiling


def _normalize_format(audio_format: str) -> str:
    """Normalize an audio format string to a pydub-compatible codec name.

    Handles MIME types, extensions with dots, and common aliases.
    """
    if not audio_format:
        return ""

    # Strip MIME type prefix if present
    fmt = audio_format.lower().strip()
    if "/" in fmt:
        fmt = fmt.split("/")[-1]
    # Strip codec parameters
    if ";" in fmt:
        fmt = fmt.split(";")[0].strip()
    # Strip leading dot
    fmt = fmt.lstrip(".")

    # Common aliases
    aliases = {
        "x-wav": "wav",
        "wave": "wav",
        "mpeg": "mp3",
        "mpeg3": "mp3",
        "mp4": "m4a",   # audio-only mp4
    }
    return aliases.get(fmt, fmt)


# ──────────────────────────────────────────────────────────────
#  FORMAT ADAPTER
# ──────────────────────────────────────────────────────────────

class FormatAdapter:
    """Audio format converter — any format → WAV 16kHz mono PCM.

    Uses pydub (which wraps ffmpeg) for format conversion.
    Pydub handles virtually every audio format that ffmpeg supports,
    making it the ideal lightweight-but-powerful choice.

    Thread-safe: each conversion operates on independent data.
    """

    def __init__(
        self,
        *,
        target_sample_rate: int = _CANONICAL_SAMPLE_RATE,
        target_channels: int = _CANONICAL_CHANNELS,
        max_size_bytes: int = _MAX_AUDIO_SIZE_BYTES,
        max_duration_seconds: float = _MAX_AUDIO_DURATION_SECONDS,
    ) -> None:
        """Initialize the FormatAdapter.

        Args:
            target_sample_rate: Output sample rate in Hz (default: 16000).
            target_channels: Output channel count (default: 1 = mono).
            max_size_bytes: Maximum input audio size to process.
            max_duration_seconds: Maximum audio duration to convert.
        """
        self._sample_rate = target_sample_rate
        self._channels = target_channels
        self._max_size = max_size_bytes
        self._max_duration = max_duration_seconds
        self._lock = threading.Lock()

        # Check pydub availability at init
        self._pydub_available = self._check_pydub()

        if not self._pydub_available:
            _logger.warning(
                "FormatAdapter: pydub not available — "
                "format conversion will be disabled. "
                "Install pydub: pip install pydub"
            )

    @staticmethod
    def _check_pydub() -> bool:
        """Check if pydub is importable."""
        try:
            import pydub  # noqa: F401
            return True
        except ImportError:
            return False

    # ── Core Conversion ───────────────────────────────────────

    def convert(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
    ) -> ConversionResult:
        """Convert audio bytes to WAV 16kHz mono PCM.

        NEVER raises — returns ConversionResult.

        Args:
            audio_bytes: Raw audio data in any supported format.
            audio_format: Hint about the input format (e.g. "ogg", "audio/mp3").

        Returns:
            ConversionResult with WAV bytes or error.
        """
        start = time.monotonic()

        # ── Validation ──
        if not audio_bytes:
            return ConversionResult(
                success=False,
                error="Empty audio bytes — nothing to convert",
                source="format_adapter",
            )

        input_size = len(audio_bytes)
        if input_size > self._max_size:
            return ConversionResult(
                success=False,
                original_size_bytes=input_size,
                error=f"Audio too large: {input_size} bytes exceeds "
                      f"limit of {self._max_size} bytes",
                source="format_adapter",
            )

        if not self._pydub_available:
            return ConversionResult(
                success=False,
                original_size_bytes=input_size,
                error="pydub not installed — format conversion unavailable. "
                      "Install pydub: pip install pydub",
                source="format_adapter",
            )

        # Normalize format string
        fmt = _normalize_format(audio_format)
        if fmt and fmt not in _SUPPORTED_INPUT_FORMATS:
            _logger.warning(
                "FormatAdapter: potentially unsupported format '%s' — "
                "attempting conversion anyway (ffmpeg may handle it)",
                fmt,
            )

        # ── Conversion ──
        try:
            wav_bytes, duration = self._do_convert(audio_bytes, fmt)
        except Exception as e:
            elapsed = time.monotonic() - start
            _logger.error(
                "FormatAdapter: conversion failed in %.2fs (format=%s, size=%d): %s",
                elapsed, fmt, input_size, e,
            )
            return ConversionResult(
                success=False,
                original_format=fmt,
                original_size_bytes=input_size,
                error=f"Conversion error: {e}",
                source="format_adapter",
            )

        elapsed = time.monotonic() - start

        # ── Duration validation ──
        if duration > self._max_duration:
            return ConversionResult(
                success=False,
                original_format=fmt,
                original_size_bytes=input_size,
                duration_seconds=duration,
                error=f"Audio too long: {duration:.1f}s exceeds "
                      f"limit of {self._max_duration:.1f}s",
                source="format_adapter",
            )

        _logger.info(
            "FormatAdapter: converted %s→wav in %.2fs "
            "(%d→%d bytes, %.1fs audio)",
            fmt or "(auto)", elapsed, input_size, len(wav_bytes), duration,
        )

        return ConversionResult(
            success=True,
            wav_bytes=wav_bytes,
            original_format=fmt,
            original_size_bytes=input_size,
            converted_size_bytes=len(wav_bytes),
            duration_seconds=duration,
            sample_rate=self._sample_rate,
            channels=self._channels,
            source="format_adapter",
        )

    async def convert_async(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
    ) -> ConversionResult:
        """Async wrapper for convert().

        Runs the synchronous conversion in a thread pool.
        """
        import asyncio
        return await asyncio.to_thread(self.convert, audio_bytes, audio_format)

    def _do_convert(
        self,
        audio_bytes: bytes,
        fmt: str,
    ) -> tuple[bytes, float]:
        """Perform the actual format conversion using pydub.

        Returns (wav_bytes, duration_seconds).

        Raises on conversion failure — caller handles exceptions.
        """
        from pydub import AudioSegment

        # Load audio from bytes
        # pydub can read from a file path or file-like object
        # For robustness, write to temp file with correct extension
        if fmt and fmt in _SUPPORTED_INPUT_FORMATS:
            suffix = f".{fmt}"
        else:
            suffix = ".wav"  # Default fallback

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Load with pydub
            load_kwargs: Dict[str, Any] = {}
            if fmt and fmt in _SUPPORTED_INPUT_FORMATS:
                load_kwargs["format"] = fmt

            try:
                audio = AudioSegment.from_file(tmp_path, **load_kwargs)
            except Exception:
                # Retry without explicit format — let ffmpeg auto-detect
                _logger.debug(
                    "FormatAdapter: retry with auto-detect (format=%s)",
                    fmt,
                )
                audio = AudioSegment.from_file(tmp_path)

            # Get duration before conversion
            duration = len(audio) / 1000.0  # pydub returns milliseconds

            # Convert to canonical format:
            #   - Set sample rate
            #   - Convert to mono
            #   - Set sample width to 16-bit
            audio = audio.set_frame_rate(self._sample_rate)
            audio = audio.set_channels(self._channels)
            audio = audio.set_sample_width(_CANONICAL_SAMPLE_WIDTH)

            # Export to WAV bytes
            buffer = io.BytesIO()
            audio.export(buffer, format=_CANONICAL_FORMAT)
            wav_bytes = buffer.getvalue()

            return wav_bytes, duration

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ── Convenience Methods ───────────────────────────────────

    def is_format_supported(self, audio_format: str) -> bool:
        """Check if an audio format is supported for conversion.

        Args:
            audio_format: Format string, MIME type, or extension.

        Returns:
            True if the format is supported for input.
        """
        fmt = _normalize_format(audio_format)
        return fmt in _SUPPORTED_INPUT_FORMATS

    def get_supported_formats(self) -> Set[str]:
        """Return the set of supported input formats."""
        return set(_SUPPORTED_INPUT_FORMATS)

    def detect_format(
        self,
        audio_bytes: bytes,
        hint: str = "",
    ) -> AudioFormat:
        """Detect the audio format from bytes and optional hint.

        Uses the hint first (if valid), then falls back to
        pydub/ffmpeg auto-detection.
        """
        # Try hint first
        if hint:
            fmt = _normalize_format(hint)
            if fmt in _SUPPORTED_INPUT_FORMATS:
                return AudioFormat.from_extension(fmt)

        # Try to detect from content using pydub
        if self._pydub_available and audio_bytes:
            try:
                from pydub import AudioSegment
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name
                try:
                    # Let pydub detect the format
                    audio = AudioSegment.from_file(tmp_path)
                    # If we got here, it loaded successfully
                    # but we don't know the exact format from pydub alone
                    return AudioFormat.UNKNOWN
                except Exception:
                    pass
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            except Exception:
                pass

        return AudioFormat.UNKNOWN

    def validate_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        *,
        max_duration: Optional[float] = None,
        max_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate audio data against size and duration limits.

        Non-destructive — does NOT convert the audio.
        Returns a dict with validation results.

        Args:
            audio_bytes: Raw audio data.
            audio_format: Format hint.
            max_duration: Override max duration (seconds).
            max_size: Override max size (bytes).

        Returns:
            Dict with keys: valid, size_valid, duration_valid,
            size_bytes, duration_seconds, errors.
        """
        errors: List[str] = []
        size_limit = max_size or self._max_size
        duration_limit = max_duration or self._max_duration

        size_bytes = len(audio_bytes) if audio_bytes else 0
        size_valid = size_bytes <= size_limit

        if not size_valid:
            errors.append(
                f"Size {size_bytes} exceeds limit {size_limit}"
            )

        # Duration requires loading the audio — lightweight check
        duration_seconds = 0.0
        duration_valid = True

        if audio_bytes and self._pydub_available:
            try:
                from pydub import AudioSegment
                fmt = _normalize_format(audio_format)
                suffix = f".{fmt}" if fmt in _SUPPORTED_INPUT_FORMATS else ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name
                try:
                    load_kwargs = {}
                    if fmt and fmt in _SUPPORTED_INPUT_FORMATS:
                        load_kwargs["format"] = fmt
                    audio = AudioSegment.from_file(tmp_path, **load_kwargs)
                    duration_seconds = len(audio) / 1000.0
                    duration_valid = duration_seconds <= duration_limit
                    if not duration_valid:
                        errors.append(
                            f"Duration {duration_seconds:.1f}s exceeds "
                            f"limit {duration_limit:.1f}s"
                        )
                except Exception as e:
                    errors.append(f"Cannot determine duration: {e}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            except Exception as e:
                errors.append(f"Duration check failed: {e}")

        return {
            "valid": len(errors) == 0,
            "size_valid": size_valid,
            "duration_valid": duration_valid,
            "size_bytes": size_bytes,
            "duration_seconds": duration_seconds,
            "errors": errors,
        }

    # ── Health & Monitoring ───────────────────────────────────

    @property
    def is_available(self) -> bool:
        """Whether format conversion is available (pydub installed)."""
        return self._pydub_available

    def health_check(self) -> Dict[str, Any]:
        """Health check for the FormatAdapter."""
        return {
            "service": "format_adapter",
            "available": self._pydub_available,
            "target_sample_rate": self._sample_rate,
            "target_channels": self._channels,
            "supported_formats": sorted(_SUPPORTED_INPUT_FORMATS),
            "max_size_bytes": self._max_size,
            "max_duration_seconds": self._max_duration,
        }


# ──────────────────────────────────────────────────────────────
#  MODULE-LEVEL CONVENIENCE
# ──────────────────────────────────────────────────────────────

# Default singleton — lazy-created on first access
_default_adapter: Optional[FormatAdapter] = None
_adapter_lock = threading.Lock()


def get_format_adapter() -> FormatAdapter:
    """Get the default FormatAdapter singleton.

    Thread-safe. Created on first access.
    """
    global _default_adapter
    if _default_adapter is not None:
        return _default_adapter

    with _adapter_lock:
        if _default_adapter is None:
            _default_adapter = FormatAdapter()
        return _default_adapter


# ──────────────────────────────────────────────────────────────
#  PUBLIC EXPORTS
# ──────────────────────────────────────────────────────────────

__all__ = [
    "FormatAdapter",
    "get_format_adapter",
    "_CANONICAL_SAMPLE_RATE",
    "_CANONICAL_CHANNELS",
    "_CANONICAL_SAMPLE_WIDTH",
    "_SUPPORTED_INPUT_FORMATS",
]
