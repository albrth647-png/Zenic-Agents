"""Tests for voice_pipeline/ear — Ear service with DummyBackend + real behavior.

Rigor: sin mocks, datos reales, cubre normal + vacío + fallback + extremos + error.
Usa DummyBackend (siempre disponible) para STT, y audio real generado con pydub.
"""

import io

import pytest
from pydub.generators import Sine

from src.core.voice_pipeline._types import (
    STTBackendConfig,
    TranscriptionResult,
)
from src.core.voice_pipeline.ear import (
    _BACKEND_CLASSES,
    _DEFAULT_FALLBACK_CHAIN,
    CloudBackend,
    DummyBackend,
    Ear,
    FasterWhisperBackend,
    STTBackend,
    WhisperBackend,
)

# ── Audio fixtures ─────────────────────────────────────────────


def _make_wav_bytes(duration_ms: int = 500) -> bytes:
    tone = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="wav")
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════
#  DummyBackend
# ════════════════════════════════════════════════════════════════


class TestDummyBackend:
    def test_name(self):
        b = DummyBackend()
        assert b.name == "dummy"

    def test_always_available(self):
        b = DummyBackend()
        assert b.is_available is True

    def test_transcribe_returns_failure(self):
        """DummyBackend NUNCA produce texto — siempre success=False."""
        b = DummyBackend()
        result = b.transcribe(b"some audio bytes", "wav")
        assert result.success is False
        assert result.transcribed_text == ""
        assert result.backend == "dummy"
        assert "no STT engine" in result.error

    def test_transcribe_empty_bytes(self):
        b = DummyBackend()
        result = b.transcribe(b"", "wav")
        assert result.success is False

    def test_health_check(self):
        b = DummyBackend()
        hc = b.health_check()
        assert hc["backend"] == "dummy"
        assert hc["available"] is True

    def test_is_stt_backend_subclass(self):
        assert issubclass(DummyBackend, STTBackend)


# ════════════════════════════════════════════════════════════════
#  FasterWhisperBackend — availability check (no model loading)
# ════════════════════════════════════════════════════════════════


class TestFasterWhisperBackend:
    def test_name(self):
        b = FasterWhisperBackend()
        assert b.name == "faster_whisper"

    def test_is_available_check(self):
        """Verifica si faster_whisper está instalado (booleano)."""
        b = FasterWhisperBackend()
        # El resultado depende del entorno — lo importante es que no raise
        result = b.is_available
        assert isinstance(result, bool)

    def test_transcribe_empty_bytes(self):
        b = FasterWhisperBackend()
        result = b.transcribe(b"", "wav")
        assert result.success is False
        assert "Empty" in result.error

    def test_health_check(self):
        b = FasterWhisperBackend()
        hc = b.health_check()
        assert hc["backend"] == "faster_whisper"
        assert "model_size" in hc


# ════════════════════════════════════════════════════════════════
#  WhisperBackend — availability check
# ════════════════════════════════════════════════════════════════


class TestWhisperBackend:
    def test_name(self):
        b = WhisperBackend()
        assert b.name == "whisper"

    def test_is_available_check(self):
        b = WhisperBackend()
        assert isinstance(b.is_available, bool)

    def test_transcribe_empty_bytes(self):
        b = WhisperBackend()
        result = b.transcribe(b"", "wav")
        assert result.success is False
        assert "Empty" in result.error


# ════════════════════════════════════════════════════════════════
#  CloudBackend — availability check
# ════════════════════════════════════════════════════════════════


class TestCloudBackend:
    def test_name(self):
        b = CloudBackend()
        assert b.name == "cloud"

    def test_not_available_without_api_key(self):
        b = CloudBackend(api_key="")
        assert b.is_available is False

    def test_transcribe_empty_bytes(self):
        b = CloudBackend()
        result = b.transcribe(b"", "wav")
        assert result.success is False
        assert "Empty" in result.error

    def test_transcribe_no_api_key(self):
        b = CloudBackend(api_key="")
        result = b.transcribe(b"some audio", "wav")
        assert result.success is False
        assert "API key" in result.error or "not configured" in result.error


# ════════════════════════════════════════════════════════════════
#  Backend Registry & Default Fallback Chain
# ════════════════════════════════════════════════════════════════


class TestBackendRegistry:
    def test_all_backends_registered(self):
        assert "dummy" in _BACKEND_CLASSES
        assert "faster_whisper" in _BACKEND_CLASSES
        assert "whisper" in _BACKEND_CLASSES
        assert "cloud" in _BACKEND_CLASSES

    def test_default_fallback_chain_order(self):
        """El orden de fallback es: faster_whisper → whisper → cloud → dummy."""
        assert _DEFAULT_FALLBACK_CHAIN == (
            "faster_whisper",
            "whisper",
            "cloud",
            "dummy",
        )

    def test_dummy_always_last_in_chain(self):
        assert _DEFAULT_FALLBACK_CHAIN[-1] == "dummy"


# ════════════════════════════════════════════════════════════════
#  Ear — Initialization & Backend Selection
# ════════════════════════════════════════════════════════════════


class TestEarInit:
    def test_default_init_selects_available_backend(self):
        """Ear auto-detecta el primer backend disponible."""
        ear = Ear()
        # En este entorno sin modelos, probablemente sea dummy
        assert ear.active_backend in (
            "faster_whisper",
            "whisper",
            "cloud",
            "dummy",
        )

    def test_explicit_dummy_backend(self):
        """Configurar solo dummy → active_backend = dummy."""
        config = STTBackendConfig(
            backend_name="dummy",
            fallback_chain=("dummy",),
        )
        ear = Ear(config=config)
        assert ear.active_backend == "dummy"

    def test_explicit_backends_list(self):
        """Pasando backends explícitos."""
        dummy = DummyBackend()
        ear = Ear(backends=[dummy])
        assert ear.active_backend == "dummy"

    def test_available_backends_list(self):
        """available_backends retorna lista de strings."""
        ear = Ear()
        backends = ear.available_backends
        assert isinstance(backends, list)
        assert "dummy" in backends  # Dummy siempre está disponible

    def test_ear_always_has_at_least_dummy(self):
        """Ear siempre tiene al menos el backend dummy."""
        config = STTBackendConfig(fallback_chain=("nonexistent_backend",))
        ear = Ear(config=config)
        # Debe crear dummy como fallback
        assert ear.active_backend == "dummy"


# ════════════════════════════════════════════════════════════════
#  Ear — transcribe() with DummyBackend
# ════════════════════════════════════════════════════════════════


class TestEarTranscribe:
    def test_transcribe_with_dummy_returns_failure(self):
        """Con DummyBackend, transcribe siempre falla."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        wav_bytes = _make_wav_bytes()
        result = ear.transcribe(wav_bytes, "wav")
        assert result.success is False
        assert result.transcribed_text == ""

    def test_transcribe_empty_bytes(self):
        """Bytes vacíos → error inmediato, no se intenta STT."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        result = ear.transcribe(b"", "wav")
        assert result.success is False
        assert "Empty" in result.error

    def test_transcribe_never_raises(self):
        """transcribe() NUNCA debe raise, sin importar el input."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        # Todos estos deben retornar un result, nunca raise
        result1 = ear.transcribe(b"", "")
        result2 = ear.transcribe(b"\x00", "xyz")
        result3 = ear.transcribe(_make_wav_bytes(), "wav")
        assert all(isinstance(r, TranscriptionResult) for r in [result1, result2, result3])

    def test_transcribe_updates_metrics(self):
        """Cada transcripción actualiza las métricas."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        wav_bytes = _make_wav_bytes()
        ear.transcribe(wav_bytes, "wav")
        ear.transcribe(wav_bytes, "wav")
        metrics = ear.metrics
        assert metrics.total_transcriptions == 2
        # Con dummy, todas son failures
        assert metrics.failed_transcriptions == 2


# ════════════════════════════════════════════════════════════════
#  Ear — Backend Switching
# ════════════════════════════════════════════════════════════════


class TestEarBackendSwitching:
    def test_switch_to_dummy(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        assert ear.switch_backend("dummy") is True
        assert ear.active_backend == "dummy"

    def test_switch_to_unavailable_backend(self):
        """Switch a backend no disponible → False."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        result = ear.switch_backend("faster_whisper")
        # Si faster_whisper no está instalado, retorna False
        # Si está instalado, retorna True — lo importante es que no raise
        assert isinstance(result, bool)

    def test_switch_to_nonexistent_backend(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        assert ear.switch_backend("nonexistent") is False


# ════════════════════════════════════════════════════════════════
#  Ear — Metrics
# ════════════════════════════════════════════════════════════════


class TestEarMetrics:
    def test_metrics_snapshot_is_copy(self):
        """metrics retorna una copia — mutar no afecta al Ear."""
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        metrics1 = ear.metrics
        metrics2 = ear.metrics
        assert metrics1 is not metrics2

    def test_metrics_initial_state(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        metrics = ear.metrics
        assert metrics.total_transcriptions == 0
        assert metrics.success_rate == 1.0  # No data = no failures


# ════════════════════════════════════════════════════════════════
#  Ear — Health Check
# ════════════════════════════════════════════════════════════════


class TestEarHealthCheck:
    def test_health_check_structure(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        hc = ear.health_check()
        assert hc["service"] == "ear"
        assert "active_backend" in hc
        assert "available_backends" in hc
        assert "all_backends" in hc
        assert "metrics" in hc

    def test_health_check_lists_all_backends(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        hc = ear.health_check()
        # Debe tener al menos 1 backend (dummy)
        assert len(hc["all_backends"]) >= 1


# ════════════════════════════════════════════════════════════════
#  Ear — transcribe_async
# ════════════════════════════════════════════════════════════════


class TestEarAsync:
    @pytest.mark.asyncio
    async def test_transcribe_async(self):
        config = STTBackendConfig(fallback_chain=("dummy",))
        ear = Ear(config=config)
        wav_bytes = _make_wav_bytes()
        result = await ear.transcribe_async(wav_bytes, "wav")
        assert isinstance(result, TranscriptionResult)
        assert result.success is False  # Dummy always fails


# ════════════════════════════════════════════════════════════════
#  STTBackend ABC — abstract contract enforcement
# ════════════════════════════════════════════════════════════════


class TestSTTBackendABC:
    def test_cannot_instantiate_abc(self):
        """STTBackend es abstracto — no se puede instanciar directamente."""
        with pytest.raises(TypeError):
            STTBackend()

    def test_concrete_backend_must_implement_methods(self):
        """Un backend sin los métodos abstractos no se puede instanciar."""

        class IncompleteBackend(STTBackend):
            pass

        with pytest.raises(TypeError):
            IncompleteBackend()
