"""Tests for VoicePipeline — unified entry point (FormatAdapter + Ear).

Rigor: sin mocks, datos reales, cubre normal + vacío + sin pipeline + extremos + error.
"""

import io

import pytest
from pydub.generators import Sine

from src.core.voice_pipeline import VoicePipeline
from src.core.voice_pipeline._types import (
    STTBackendConfig,
    TranscriptionResult,
)
from src.core.voice_pipeline.ear import Ear
from src.core.voice_pipeline.format_adapter import FormatAdapter

# ── Audio fixtures ─────────────────────────────────────────────


def _make_wav_bytes(duration_ms: int = 500) -> bytes:
    tone = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="wav")
    return buf.getvalue()


def _make_ogg_bytes(duration_ms: int = 500) -> bytes:
    tone = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="ogg")
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════
#  VoicePipeline — Construction
# ════════════════════════════════════════════════════════════════


class TestVoicePipelineInit:
    def test_default_construction(self):
        vp = VoicePipeline()
        assert vp.active_backend in (
            "faster_whisper",
            "whisper",
            "cloud",
            "dummy",
        )
        assert vp.adapter is not None
        assert vp.ear is not None

    def test_with_dummy_config(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        assert vp.active_backend == "dummy"

    def test_with_custom_adapter_and_ear(self):
        adapter = FormatAdapter()
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        vp = VoicePipeline(format_adapter=adapter, ear=ear)
        assert vp.active_backend == "dummy"
        assert vp.adapter is adapter
        assert vp.ear is ear


# ════════════════════════════════════════════════════════════════
#  VoicePipeline — process() with real audio
# ════════════════════════════════════════════════════════════════


class TestVoicePipelineProcess:
    def test_process_wav_with_dummy(self):
        """WAV → FormatAdapter pass-through → DummyBackend → failure (no STT)."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        wav_bytes = _make_wav_bytes()
        result = vp.process(wav_bytes, "wav")
        assert isinstance(result, TranscriptionResult)
        # Dummy no transcribe → success=False
        assert result.success is False

    def test_process_ogg_with_dummy(self):
        """OGG → FormatAdapter converts → DummyBackend → failure."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        ogg_bytes = _make_ogg_bytes()
        result = vp.process(ogg_bytes, "ogg")
        assert isinstance(result, TranscriptionResult)
        # OGG conversion should work, but dummy can't transcribe
        assert result.success is False

    def test_process_empty_bytes(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        result = vp.process(b"", "wav")
        assert result.success is False
        assert "Empty" in result.error

    def test_process_garbage_bytes(self):
        """Bytes basura con formato OGG → conversion failure → error."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        result = vp.process(b"\x00\x01\x02" * 100, "ogg")
        assert result.success is False

    def test_process_never_raises(self):
        """process() NUNCA debe raise."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        # Estos no deben raise nunca
        r1 = vp.process(b"", "")
        r2 = vp.process(b"\x00", "xyz")
        r3 = vp.process(_make_wav_bytes(), "wav")
        assert all(isinstance(r, TranscriptionResult) for r in [r1, r2, r3])

    def test_process_preserves_audio_format_in_result(self):
        """Después de OGG→WAV conversion, Ear recibe WAV. El audio_format
        del resultado es 'wav' (formato del input que recibió Ear),
        no 'ogg' (formato original). Esto es correcto: el resultado
        refleja lo que procesó el backend, no la fuente original."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        ogg_bytes = _make_ogg_bytes()
        result = vp.process(ogg_bytes, "ogg")
        # After conversion, Ear receives WAV → audio_format = "wav"
        assert result.audio_format == "wav"

    def test_process_wav_no_conversion_needed(self):
        """WAV no necesita conversión — debe pasar directo al STT."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        wav_bytes = _make_wav_bytes()
        result = vp.process(wav_bytes, "wav")
        # El resultado debe tener audio_format=wav
        assert result.audio_format == "wav"


# ════════════════════════════════════════════════════════════════
#  VoicePipeline — process_async
# ════════════════════════════════════════════════════════════════


class TestVoicePipelineAsync:
    @pytest.mark.asyncio
    async def test_process_async(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        wav_bytes = _make_wav_bytes()
        result = await vp.process_async(wav_bytes, "wav")
        assert isinstance(result, TranscriptionResult)
        assert result.success is False  # Dummy

    @pytest.mark.asyncio
    async def test_process_async_ogg(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        ogg_bytes = _make_ogg_bytes()
        result = await vp.process_async(ogg_bytes, "ogg")
        assert isinstance(result, TranscriptionResult)


# ════════════════════════════════════════════════════════════════
#  VoicePipeline — Health Check
# ════════════════════════════════════════════════════════════════


class TestVoicePipelineHealthCheck:
    def test_health_check_structure(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        hc = vp.health_check()
        assert hc["service"] == "voice_pipeline"
        assert "format_adapter" in hc
        assert "ear" in hc
        assert hc["format_adapter"]["available"] is True

    def test_available_backends(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        backends = vp.available_backends
        assert "dummy" in backends


# ════════════════════════════════════════════════════════════════
#  VoicePipeline — INBOUND ONLY invariant
# ════════════════════════════════════════════════════════════════


class TestVoicePipelineInboundOnly:
    def test_no_tts_capability(self):
        """VoicePipeline NO tiene capacidad de TTS — solo audio→text."""
        vp = VoicePipeline()
        # Verificar que no hay métodos de TTS
        assert not hasattr(vp, "synthesize")
        assert not hasattr(vp, "text_to_speech")
        assert not hasattr(vp, "tts")

    def test_process_returns_transcription_only(self):
        """process() siempre retorna TranscriptionResult — texto, nunca audio."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        vp = VoicePipeline(stt_config=config)
        wav_bytes = _make_wav_bytes()
        result = vp.process(wav_bytes, "wav")
        assert isinstance(result, TranscriptionResult)
        # No hay audio de salida en el resultado
        assert not hasattr(result, "audio_bytes")
        assert not hasattr(result, "output_audio")
