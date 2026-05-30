"""Tests for voice_pipeline/format_adapter — FormatAdapter with REAL audio.

Rigor: sin mocks, datos reales (pydub+ffmpeg generan audio), cubre normal +
vacío + tipo incorrecto + valores extremos + error de sistema.
"""

import io

import pytest
from pydub.generators import Sine

from src.core.voice_pipeline._types import AudioFormat
from src.core.voice_pipeline.format_adapter import (
    _CANONICAL_CHANNELS,
    _CANONICAL_SAMPLE_RATE,
    FormatAdapter,
    _normalize_format,
    get_format_adapter,
)

# ── Audio fixtures: REAL audio bytes ────────────────────────────


def _make_wav_bytes(duration_ms: int = 1000, freq: int = 440) -> bytes:
    """Generate real WAV audio bytes using pydub."""
    tone = Sine(freq).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="wav")
    return buf.getvalue()


def _make_ogg_bytes(duration_ms: int = 1000, freq: int = 440) -> bytes:
    """Generate real OGG/Opus audio bytes (WhatsApp format)."""
    tone = Sine(freq).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="ogg")
    return buf.getvalue()


def _make_mp3_bytes(duration_ms: int = 1000, freq: int = 440) -> bytes:
    """Generate real MP3 audio bytes."""
    tone = Sine(freq).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="mp3")
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════
#  _normalize_format
# ════════════════════════════════════════════════════════════════


class TestNormalizeFormat:
    def test_simple_extension(self):
        assert _normalize_format("ogg") == "ogg"
        assert _normalize_format("mp3") == "mp3"
        assert _normalize_format("wav") == "wav"

    def test_mime_type(self):
        assert _normalize_format("audio/ogg") == "ogg"
        assert _normalize_format("audio/mpeg") == "mp3"

    def test_mime_with_codec(self):
        assert _normalize_format("audio/ogg; codecs=opus") == "ogg"

    def test_with_dot(self):
        assert _normalize_format(".ogg") == "ogg"
        assert _normalize_format(".mp3") == "mp3"

    def test_aliases(self):
        assert _normalize_format("x-wav") == "wav"
        assert _normalize_format("wave") == "wav"
        assert _normalize_format("mpeg") == "mp3"
        assert _normalize_format("mp4") == "m4a"

    def test_empty(self):
        assert _normalize_format("") == ""

    def test_case_insensitive(self):
        assert _normalize_format("OGG") == "ogg"
        assert _normalize_format("Audio/MP3") == "mp3"

    def test_unknown_format(self):
        assert _normalize_format("xyz") == "xyz"  # No alias → passes through


# ════════════════════════════════════════════════════════════════
#  FormatAdapter — Construction & Availability
# ════════════════════════════════════════════════════════════════


class TestFormatAdapterInit:
    def test_default_construction(self):
        adapter = FormatAdapter()
        assert adapter.is_available is True
        assert adapter._sample_rate == _CANONICAL_SAMPLE_RATE
        assert adapter._channels == _CANONICAL_CHANNELS

    def test_custom_sample_rate(self):
        adapter = FormatAdapter(target_sample_rate=8000)
        assert adapter._sample_rate == 8000

    def test_custom_channels(self):
        adapter = FormatAdapter(target_channels=2)
        assert adapter._channels == 2

    def test_health_check_structure(self):
        adapter = FormatAdapter()
        hc = adapter.health_check()
        assert hc["service"] == "format_adapter"
        assert hc["available"] is True
        assert "supported_formats" in hc
        assert "wav" in hc["supported_formats"]


# ════════════════════════════════════════════════════════════════
#  FormatAdapter — convert() with REAL audio
# ════════════════════════════════════════════════════════════════


class TestFormatAdapterConvert:
    def test_convert_wav_to_wav(self):
        """WAV → WAV: passthrough, debe funcionar."""
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        result = adapter.convert(wav_bytes, "wav")
        assert result.success is True
        assert len(result.wav_bytes) > 0
        assert result.sample_rate == _CANONICAL_SAMPLE_RATE
        assert result.channels == _CANONICAL_CHANNELS
        assert result.duration_seconds > 0

    def test_convert_ogg_to_wav(self):
        """OGG → WAV: caso principal de WhatsApp."""
        adapter = FormatAdapter()
        ogg_bytes = _make_ogg_bytes(500)
        result = adapter.convert(ogg_bytes, "ogg")
        assert result.success is True
        assert len(result.wav_bytes) > 0
        assert result.sample_rate == _CANONICAL_SAMPLE_RATE
        assert result.channels == _CANONICAL_CHANNELS

    def test_convert_mp3_to_wav(self):
        """MP3 → WAV: caso genérico."""
        adapter = FormatAdapter()
        mp3_bytes = _make_mp3_bytes(500)
        result = adapter.convert(mp3_bytes, "mp3")
        assert result.success is True
        assert len(result.wav_bytes) > 0

    def test_convert_empty_bytes(self):
        """Bytes vacíos → error claro, nunca raise."""
        adapter = FormatAdapter()
        result = adapter.convert(b"", "ogg")
        assert result.success is False
        assert "Empty" in result.error

    def test_convert_garbage_bytes(self):
        """Bytes basura → error de conversión, nunca raise."""
        adapter = FormatAdapter()
        result = adapter.convert(b"\x00\x01\x02\x03" * 100, "ogg")
        assert result.success is False
        assert result.error != ""

    def test_convert_too_large(self):
        """Audio que excede max_size_bytes → error claro."""
        adapter = FormatAdapter(max_size_bytes=100)
        wav_bytes = _make_wav_bytes(500)
        result = adapter.convert(wav_bytes, "wav")
        assert result.success is False
        assert "too large" in result.error.lower() or "exceeds" in result.error.lower()

    def test_convert_mime_type_format(self):
        """Formato como MIME type (audio/ogg) debe funcionar."""
        adapter = FormatAdapter()
        ogg_bytes = _make_ogg_bytes(500)
        result = adapter.convert(ogg_bytes, "audio/ogg")
        assert result.success is True

    def test_convert_no_format_hint(self):
        """Sin hint de formato → pydub debe auto-detectar."""
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        result = adapter.convert(wav_bytes, "")
        assert result.success is True

    def test_convert_result_has_correct_sizes(self):
        """original_size_bytes y converted_size_bytes deben ser coherentes."""
        adapter = FormatAdapter()
        ogg_bytes = _make_ogg_bytes(500)
        result = adapter.convert(ogg_bytes, "ogg")
        assert result.success is True
        assert result.original_size_bytes == len(ogg_bytes)
        assert result.converted_size_bytes == len(result.wav_bytes)
        # WAV is typically larger than OGG
        assert result.converted_size_bytes > 0

    def test_convert_preserves_duration(self):
        """La duración del audio debe preservarse."""
        adapter = FormatAdapter()
        ogg_bytes = _make_ogg_bytes(2000)  # 2 seconds
        result = adapter.convert(ogg_bytes, "ogg")
        assert result.success is True
        # Duration should be ~2 seconds (allow some tolerance)
        assert 1.5 < result.duration_seconds < 2.5


# ════════════════════════════════════════════════════════════════
#  FormatAdapter — validate_audio()
# ════════════════════════════════════════════════════════════════


class TestFormatAdapterValidate:
    def test_validate_valid_audio(self):
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        result = adapter.validate_audio(wav_bytes, "wav")
        assert result["valid"] is True
        assert result["size_valid"] is True
        assert result["duration_valid"] is True

    def test_validate_empty_bytes(self):
        adapter = FormatAdapter()
        result = adapter.validate_audio(b"", "wav")
        assert result["valid"] is True  # Empty bytes don't violate limits
        assert result["size_bytes"] == 0

    def test_validate_too_large(self):
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        result = adapter.validate_audio(wav_bytes, "wav", max_size=10)
        assert result["size_valid"] is False
        assert result["valid"] is False


# ════════════════════════════════════════════════════════════════
#  FormatAdapter — is_format_supported() / detect_format()
# ════════════════════════════════════════════════════════════════


class TestFormatAdapterSupport:
    def test_supported_formats(self):
        adapter = FormatAdapter()
        supported = adapter.get_supported_formats()
        assert "ogg" in supported
        assert "mp3" in supported
        assert "wav" in supported
        assert "m4a" in supported
        assert "opus" in supported

    def test_is_format_supported(self):
        adapter = FormatAdapter()
        assert adapter.is_format_supported("ogg") is True
        assert adapter.is_format_supported("audio/ogg") is True
        assert adapter.is_format_supported("xyz") is False

    def test_detect_format_with_hint(self):
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        fmt = adapter.detect_format(wav_bytes, hint="ogg")
        assert fmt == AudioFormat.OGG

    def test_detect_format_empty_hint(self):
        adapter = FormatAdapter()
        wav_bytes = _make_wav_bytes(500)
        fmt = adapter.detect_format(wav_bytes, hint="")
        # Without hint, pydub may not determine format exactly
        assert isinstance(fmt, AudioFormat)

    def test_detect_format_empty_bytes(self):
        adapter = FormatAdapter()
        fmt = adapter.detect_format(b"", hint="ogg")
        # Empty bytes with hint returns the hint format
        assert fmt == AudioFormat.OGG


# ════════════════════════════════════════════════════════════════
#  get_format_adapter — Singleton
# ════════════════════════════════════════════════════════════════


class TestGetFormatAdapter:
    def test_singleton_returns_same_instance(self):
        a = get_format_adapter()
        b = get_format_adapter()
        assert a is b

    def test_singleton_is_available(self):
        adapter = get_format_adapter()
        assert adapter.is_available is True


# ════════════════════════════════════════════════════════════════
#  FormatAdapter — convert_async (real async test)
# ════════════════════════════════════════════════════════════════


class TestFormatAdapterAsync:
    @pytest.mark.asyncio
    async def test_convert_async_ogg(self):
        """convert_async debe producir el mismo resultado que convert."""
        adapter = FormatAdapter()
        ogg_bytes = _make_ogg_bytes(500)
        result = await adapter.convert_async(ogg_bytes, "ogg")
        assert result.success is True
        assert len(result.wav_bytes) > 0
