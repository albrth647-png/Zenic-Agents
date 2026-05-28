"""Tests for _transport_types — VoiceChannelInput/Result, TextChannelInput/Result.

Rigor: sin mocks, datos reales. Casos: normal + vacío + nulo + tipo incorrecto +
valores extremos + error de sistema. Si un test no puede fallar, no se escribe.
"""

import pytest

from src.core.agents.schemas.types._transport_types import (
    TextChannelInput,
    TextChannelResult,
    VoiceChannelInput,
    VoiceChannelResult,
)

# ════════════════════════════════════════════════════════════════
#  TextChannelInput
# ════════════════════════════════════════════════════════════════

class TestTextChannelInput:

    def test_defaults_all_empty_or_zero(self):
        """Todos los campos deben tener defaults seguros — nunca raise."""
        inp = TextChannelInput()
        assert inp.text == ""
        assert inp.channel == ""
        assert inp.recipient == ""
        assert inp.priority == "normal"
        assert inp.reply_to == ""
        assert inp.thread_id == ""
        assert inp.metadata == {}
        assert inp.max_chunks == 10
        assert inp.fallback_channels == ()

    def test_normal_construction(self):
        inp = TextChannelInput(
            text="Hola mundo",
            channel="whatsapp",
            recipient="+535551234",
            priority="urgent",
            reply_to="msg_001",
            thread_id="thread_42",
            metadata={"session_id": "abc"},
            max_chunks=5,
            fallback_channels=("telegram", "sms"),
        )
        assert inp.text == "Hola mundo"
        assert inp.channel == "whatsapp"
        assert inp.recipient == "+535551234"
        assert inp.priority == "urgent"
        assert inp.metadata["session_id"] == "abc"
        assert len(inp.fallback_channels) == 2

    def test_empty_string_fields(self):
        """Strings vacíos son válidos — nunca raise."""
        inp = TextChannelInput(text="", channel="", recipient="")
        assert inp.text == ""
        assert inp.channel == ""

    def test_very_long_text(self):
        """Texto extremadamente largo — no rompe la estructura."""
        long_text = "A" * 1_000_000
        inp = TextChannelInput(text=long_text, channel="log")
        assert len(inp.text) == 1_000_000

    def test_metadata_mutable_default_isolation(self):
        """Dos instancias sin metadata no comparten el mismo dict."""
        a = TextChannelInput()
        b = TextChannelInput()
        a.metadata["key"] = "value"
        assert "key" not in b.metadata

    def test_fallback_channels_as_list_converts(self):
        """Si se pasa una lista en vez de tuple, funciona pero es Sequence."""
        inp = TextChannelInput(fallback_channels=["a", "b"])
        assert list(inp.fallback_channels) == ["a", "b"]

    def test_max_chunks_zero(self):
        """max_chunks=0 es permitido por el dataclass — el agente lo maneja."""
        inp = TextChannelInput(max_chunks=0)
        assert inp.max_chunks == 0

    def test_negative_max_chunks(self):
        """Valor extremo: max_chunks negativo — el dataclass lo permite."""
        inp = TextChannelInput(max_chunks=-1)
        assert inp.max_chunks == -1

    def test_priority_non_standard(self):
        """Prioridad no estándar — el dataclass la acepta, el agente decide."""
        inp = TextChannelInput(priority="super_urgent")
        assert inp.priority == "super_urgent"


# ════════════════════════════════════════════════════════════════
#  TextChannelResult
# ════════════════════════════════════════════════════════════════

class TestTextChannelResult:

    def test_defaults_indicate_failure(self):
        """Defaults deben indicar fallo (success=False, status=pending)."""
        res = TextChannelResult()
        assert res.success is False
        assert res.status == "pending"
        assert res.channel_used == ""
        assert res.messages_sent == 0
        assert res.truncated is False
        assert res.fallback_used is False
        assert res.source == "deterministic"

    def test_normal_success_result(self):
        res = TextChannelResult(
            success=True,
            channel_used="whatsapp",
            original_channel="whatsapp",
            messages_sent=2,
            message_ids=["id1", "id2"],
            status="sent",
            original_length=5000,
            delivered_length=4990,
        )
        assert res.success is True
        assert res.messages_sent == 2
        assert len(res.message_ids) == 2

    def test_message_ids_mutable_default_isolation(self):
        """Dos instancias sin message_ids no comparten la misma lista."""
        a = TextChannelResult()
        b = TextChannelResult()
        a.message_ids.append("x")
        assert b.message_ids == []

    def test_error_field_on_failure(self):
        res = TextChannelResult(
            success=False,
            error="Connection timeout",
            source="fallback",
        )
        assert "timeout" in res.error
        assert res.source == "fallback"

    def test_split_count_consistency(self):
        """split_count=0 significa que no hubo split."""
        res = TextChannelResult(split_count=0)
        assert res.split_count == 0
        res2 = TextChannelResult(split_count=5)
        assert res2.split_count == 5

    def test_truncated_and_fallback_independent(self):
        """Truncado y fallback son ortogonales."""
        res = TextChannelResult(truncated=True, fallback_used=False)
        assert res.truncated is True
        assert res.fallback_used is False


# ════════════════════════════════════════════════════════════════
#  VoiceChannelInput
# ════════════════════════════════════════════════════════════════

class TestVoiceChannelInput:

    def test_defaults_all_empty(self):
        inp = VoiceChannelInput()
        assert inp.audio_url == ""
        assert inp.audio_path == ""
        assert inp.audio_format == ""
        assert inp.channel == ""
        assert inp.sender == ""
        assert inp.duration_seconds == 0.0
        assert inp.metadata == {}

    def test_normal_construction_with_url(self):
        inp = VoiceChannelInput(
            audio_url="https://api.whatsapp.com/media/123",
            audio_format="ogg",
            channel="whatsapp",
            sender="+535551234",
            duration_seconds=15.5,
        )
        assert "whatsapp.com" in inp.audio_url
        assert inp.audio_format == "ogg"
        assert inp.duration_seconds == 15.5

    def test_normal_construction_with_path(self):
        inp = VoiceChannelInput(
            audio_path="/tmp/voice_note.ogg",  # noqa: S108
            audio_format="ogg",
            channel="local",
        )
        assert inp.audio_path == "/tmp/voice_note.ogg"  # noqa: S108

    def test_empty_url_and_path(self):
        """Sin fuente de audio — el agente lo detecta como error."""
        inp = VoiceChannelInput()
        assert not inp.audio_url and not inp.audio_path

    def test_both_sources_present(self):
        """URL y path simultáneos — el agente decide prioridad."""
        inp = VoiceChannelInput(
            audio_url="https://example.com/audio.mp3",
            audio_path="/tmp/audio.mp3",  # noqa: S108
        )
        assert inp.audio_url and inp.audio_path

    def test_metadata_mutable_default_isolation(self):
        a = VoiceChannelInput()
        b = VoiceChannelInput()
        a.metadata["lang"] = "es"
        assert "lang" not in b.metadata

    def test_duration_zero_and_negative(self):
        """Valores extremos de duración — el dataclass los permite."""
        inp = VoiceChannelInput(duration_seconds=0.0)
        assert inp.duration_seconds == 0.0
        inp2 = VoiceChannelInput(duration_seconds=-5.0)
        assert inp2.duration_seconds == -5.0

    def test_very_long_url(self):
        url = "https://example.com/" + "a" * 10_000
        inp = VoiceChannelInput(audio_url=url)
        assert len(inp.audio_url) > 10_000


# ════════════════════════════════════════════════════════════════
#  VoiceChannelResult
# ════════════════════════════════════════════════════════════════

class TestVoiceChannelResult:

    def test_defaults_indicate_failure(self):
        res = VoiceChannelResult()
        assert res.success is False
        assert res.transcribed_text == ""
        assert res.confidence == 0.0
        assert res.source == "deterministic"

    def test_normal_success_result(self):
        res = VoiceChannelResult(
            success=True,
            transcribed_text="Hola, necesito ayuda con mi cuenta",
            channel="whatsapp",
            audio_format="ogg",
            duration_seconds=8.3,
            confidence=0.92,
            language="es",
        )
        assert res.success is True
        assert "Hola" in res.transcribed_text
        assert res.confidence > 0.9
        assert res.language == "es"

    def test_confidence_bounds(self):
        """Confidence fuera de rango [0,1] — el dataclass lo permite,
        pero es responsabilidad del productor mantener el rango."""
        res = VoiceChannelResult(confidence=1.5)
        assert res.confidence == 1.5  # El test documenta el comportamiento
        res2 = VoiceChannelResult(confidence=-0.1)
        assert res2.confidence == -0.1

    def test_error_result(self):
        res = VoiceChannelResult(
            success=False,
            error="STT backend unavailable",
            source="fallback",
        )
        assert "unavailable" in res.error
        assert res.source == "fallback"
        assert res.transcribed_text == ""

    def test_empty_transcription_on_success(self):
        """Success=True pero transcribed_text vacío — posible pero inusual."""
        res = VoiceChannelResult(success=True, transcribed_text="")
        assert res.success is True
        assert res.transcribed_text == ""

    def test_source_trace(self):
        """El campo source siempre debe estar presente para auditoría."""
        for source in ["deterministic", "fallback", "ear", "voice_pipeline", "dummy"]:
            res = VoiceChannelResult(source=source)
            assert res.source == source
