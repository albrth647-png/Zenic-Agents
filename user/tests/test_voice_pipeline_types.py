"""Tests for voice_pipeline/_types — AudioFormat, TranscriptionResult, ConversionResult,
STTBackendConfig, VoicePipelineMetrics.

Rigor: sin mocks, datos reales, cubre normal + vacío + nulo + extremos + error.
"""

import pytest

from src.core.voice_pipeline._types import (
    AudioFormat,
    ConversionResult,
    STTBackendConfig,
    TranscriptionResult,
    VoicePipelineMetrics,
)

# ════════════════════════════════════════════════════════════════
#  AudioFormat enum
# ════════════════════════════════════════════════════════════════

class TestAudioFormat:

    def test_all_formats_exist(self):
        """Todos los formatos definidos deben estar en el enum."""
        expected = {"OGG", "MP3", "WAV", "M4A", "OPUS", "WEBM", "AMR", "AAC", "FLAC", "UNKNOWN"}
        actual = {f.name for f in AudioFormat}
        assert expected == actual

    def test_from_mime_common_types(self):
        """MIME types comunes de canales deben mapear correctamente."""
        assert AudioFormat.from_mime("audio/ogg") == AudioFormat.OGG
        assert AudioFormat.from_mime("audio/mpeg") == AudioFormat.MP3
        assert AudioFormat.from_mime("audio/mp4") == AudioFormat.M4A
        assert AudioFormat.from_mime("audio/wav") == AudioFormat.WAV
        assert AudioFormat.from_mime("audio/x-wav") == AudioFormat.WAV
        assert AudioFormat.from_mime("audio/webm") == AudioFormat.WEBM
        assert AudioFormat.from_mime("audio/flac") == AudioFormat.FLAC
        assert AudioFormat.from_mime("audio/amr") == AudioFormat.AMR
        assert AudioFormat.from_mime("audio/aac") == AudioFormat.AAC
        assert AudioFormat.from_mime("audio/opus") == AudioFormat.OPUS

    def test_from_mime_with_codec_parameter(self):
        """MIME type con parámetro codecs= debe ignorar el parámetro."""
        assert AudioFormat.from_mime("audio/ogg; codecs=opus") == AudioFormat.OGG

    def test_from_mime_empty_and_none_like(self):
        """Strings vacíos o None-like deben devolver UNKNOWN."""
        assert AudioFormat.from_mime("") == AudioFormat.UNKNOWN
        assert AudioFormat.from_mime("   ") == AudioFormat.UNKNOWN

    def test_from_mime_unknown_type(self):
        """MIME type desconocido → UNKNOWN."""
        assert AudioFormat.from_mime("video/mp4") == AudioFormat.UNKNOWN
        assert AudioFormat.from_mime("application/json") == AudioFormat.UNKNOWN

    def test_from_mime_case_insensitive(self):
        """MIME types deben ser case-insensitive."""
        assert AudioFormat.from_mime("Audio/OGG") == AudioFormat.OGG
        assert AudioFormat.from_mime("AUDIO/MPEG") == AudioFormat.MP3

    def test_from_extension_common(self):
        """Extensiones comunes deben mapear correctamente."""
        assert AudioFormat.from_extension("ogg") == AudioFormat.OGG
        assert AudioFormat.from_extension("mp3") == AudioFormat.MP3
        assert AudioFormat.from_extension("wav") == AudioFormat.WAV
        assert AudioFormat.from_extension("m4a") == AudioFormat.M4A
        assert AudioFormat.from_extension("opus") == AudioFormat.OPUS
        assert AudioFormat.from_extension("webm") == AudioFormat.WEBM
        assert AudioFormat.from_extension("flac") == AudioFormat.FLAC

    def test_from_extension_with_dot(self):
        """Extensiones con punto deben funcionar."""
        assert AudioFormat.from_extension(".ogg") == AudioFormat.OGG
        assert AudioFormat.from_extension(".mp3") == AudioFormat.MP3

    def test_from_extension_aliases(self):
        """Aliases de extensión."""
        assert AudioFormat.from_extension("oga") == AudioFormat.OGG
        assert AudioFormat.from_extension("wave") == AudioFormat.WAV
        assert AudioFormat.from_extension("mp4") == AudioFormat.M4A  # audio-only mp4

    def test_from_extension_empty(self):
        assert AudioFormat.from_extension("") == AudioFormat.UNKNOWN

    def test_from_extension_unknown(self):
        assert AudioFormat.from_extension("xyz") == AudioFormat.UNKNOWN

    def test_from_extension_case_insensitive(self):
        assert AudioFormat.from_extension("OGG") == AudioFormat.OGG
        assert AudioFormat.from_extension("Mp3") == AudioFormat.MP3

    def test_enum_is_string(self):
        """AudioFormat hereda de str + Enum → se puede comparar con strings."""
        assert AudioFormat.OGG == "ogg"
        assert AudioFormat.WAV == "wav"
        assert AudioFormat.UNKNOWN == "unknown"


# ════════════════════════════════════════════════════════════════
#  TranscriptionResult
# ════════════════════════════════════════════════════════════════

class TestTranscriptionResult:

    def test_defaults_indicate_failure(self):
        res = TranscriptionResult()
        assert res.success is False
        assert res.transcribed_text == ""
        assert res.confidence == 0.0
        assert res.language == ""
        assert res.backend == ""
        assert res.source == "deterministic"

    def test_normal_success(self):
        res = TranscriptionResult(
            success=True,
            transcribed_text="Buenos días",
            confidence=0.85,
            language="es",
            duration_seconds=3.2,
            backend="faster_whisper",
        )
        assert res.success is True
        assert res.transcribed_text == "Buenos días"

    def test_is_empty_property(self):
        res = TranscriptionResult(transcribed_text="")
        assert res.is_empty is True
        res2 = TranscriptionResult(transcribed_text="   ")
        assert res2.is_empty is True  # Solo whitespace → vacío
        res3 = TranscriptionResult(transcribed_text="Hola")
        assert res3.is_empty is False

    def test_text_preview_property(self):
        long_text = "A" * 500
        res = TranscriptionResult(transcribed_text=long_text)
        assert len(res.text_preview) == 200
        assert res.text_preview == "A" * 200

    def test_text_preview_short_text(self):
        res = TranscriptionResult(transcribed_text="Hola")
        assert res.text_preview == "Hola"

    def test_error_result(self):
        res = TranscriptionResult(
            success=False,
            error="Model not loaded",
            backend="whisper",
        )
        assert "not loaded" in res.error
        assert res.backend == "whisper"


# ════════════════════════════════════════════════════════════════
#  ConversionResult
# ════════════════════════════════════════════════════════════════

class TestConversionResult:

    def test_defaults_indicate_failure(self):
        res = ConversionResult()
        assert res.success is False
        assert res.wav_bytes == b""
        assert res.sample_rate == 16000
        assert res.channels == 1
        assert res.source == "deterministic"

    def test_normal_success(self):
        res = ConversionResult(
            success=True,
            wav_bytes=b"\x00" * 1000,
            original_format="ogg",
            original_size_bytes=500,
            converted_size_bytes=1000,
            duration_seconds=5.0,
        )
        assert res.success is True
        assert len(res.wav_bytes) == 1000
        assert res.original_format == "ogg"

    def test_empty_wav_bytes_on_failure(self):
        res = ConversionResult(success=False, error="Conversion error")
        assert res.wav_bytes == b""


# ════════════════════════════════════════════════════════════════
#  STTBackendConfig
# ════════════════════════════════════════════════════════════════

class TestSTTBackendConfig:

    def test_defaults(self):
        cfg = STTBackendConfig()
        assert cfg.backend_name == "auto"
        assert cfg.model_size == "base"
        assert cfg.device == "cpu"
        assert cfg.compute_type == "int8"
        assert cfg.api_key == ""
        assert cfg.timeout_seconds == 30.0
        assert cfg.max_audio_seconds == 600.0
        assert cfg.fallback_chain == ()

    def test_explicit_config(self):
        cfg = STTBackendConfig(
            backend_name="faster_whisper",
            model_size="small",
            device="cuda",
            compute_type="float16",
            api_key="sk-test",
            fallback_chain=("faster_whisper", "dummy"),
        )
        assert cfg.backend_name == "faster_whisper"
        assert cfg.fallback_chain == ("faster_whisper", "dummy")

    def test_fallback_chain_mutable_default_isolation(self):
        a = STTBackendConfig()
        b = STTBackendConfig()
        # fallback_chain is () by default, immutable tuple, no isolation issue
        assert a.fallback_chain == b.fallback_chain == ()


# ════════════════════════════════════════════════════════════════
#  VoicePipelineMetrics
# ════════════════════════════════════════════════════════════════

class TestVoicePipelineMetrics:

    def test_defaults(self):
        m = VoicePipelineMetrics()
        assert m.total_transcriptions == 0
        assert m.successful_transcriptions == 0
        assert m.failed_transcriptions == 0
        assert m.total_audio_seconds == 0.0
        assert m.backend_usage == {}

    def test_success_rate_no_transcriptions(self):
        """Sin transcripciones → success_rate = 1.0 (no data = no failures)."""
        m = VoicePipelineMetrics()
        assert m.success_rate == 1.0

    def test_success_rate_calculation(self):
        m = VoicePipelineMetrics(
            total_transcriptions=10,
            successful_transcriptions=8,
            failed_transcriptions=2,
        )
        assert m.success_rate == 0.8

    def test_success_rate_all_failed(self):
        m = VoicePipelineMetrics(
            total_transcriptions=5,
            successful_transcriptions=0,
            failed_transcriptions=5,
        )
        assert m.success_rate == 0.0

    def test_success_rate_all_succeeded(self):
        m = VoicePipelineMetrics(
            total_transcriptions=3,
            successful_transcriptions=3,
        )
        assert m.success_rate == 1.0

    def test_backend_usage_dict(self):
        m = VoicePipelineMetrics(backend_usage={"dummy": 5, "whisper": 3})
        assert m.backend_usage["dummy"] == 5
        assert m.backend_usage["whisper"] == 3

    def test_backend_usage_mutable_default_isolation(self):
        a = VoicePipelineMetrics()
        b = VoicePipelineMetrics()
        a.backend_usage["test"] = 1
        assert "test" not in b.backend_usage
