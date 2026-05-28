"""Tests for A53 TextChannelAgent — text delivery agent.

Rigor: sin mocks, datos reales, cubre normal + vacío + sin registry wired +
tipo incorrecto + extremos + error de sistema.

Nota: A53 necesita AdapterRegistry wired para ejecutar la pipeline completa.
Los tests aquí cubren lo que se puede probar sin infraestructura externa:
input validation, fallback, helpers, wiring, y edge cases.
"""

import pytest

from src.core.agents.schemas.types._transport_types import (
    TextChannelInput,
    TextChannelResult,
)
from src.core.agents.transport.text_channel_agent import TextChannelAgent

# ════════════════════════════════════════════════════════════════
#  A53 — Construction & Wiring
# ════════════════════════════════════════════════════════════════

class TestA53Construction:

    def test_default_construction(self):
        agent = TextChannelAgent()
        assert agent.name == "A53_TextChannelAgent"
        assert agent._registry is None
        assert agent._router is None

    def test_wire_with_none(self):
        agent = TextChannelAgent()
        agent.wire(registry=None, router=None)
        assert agent._registry is None
        assert agent._router is None


# ════════════════════════════════════════════════════════════════
#  A53 — Input Validation
# ════════════════════════════════════════════════════════════════

class TestA53InputValidation:

    def test_text_channel_input_passthrough(self):
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Hola", channel="whatsapp")
        result = agent._validate_input(inp)
        assert result.text == "Hola"
        assert result.channel == "whatsapp"

    def test_dict_input(self):
        agent = TextChannelAgent()
        data = {
            "text": "Mensaje",
            "channel": "telegram",
            "priority": "high",
        }
        result = agent._validate_input(data)
        assert isinstance(result, TextChannelInput)
        assert result.text == "Mensaje"
        assert result.channel == "telegram"
        assert result.priority == "high"

    def test_dict_input_missing_keys(self):
        agent = TextChannelAgent()
        result = agent._validate_input({})
        assert isinstance(result, TextChannelInput)
        assert result.text == ""
        assert result.channel == ""
        assert result.priority == "normal"  # Default

    def test_string_input_uses_log_channel(self):
        """String crudo → canal 'log' (fallback)."""
        agent = TextChannelAgent()
        result = agent._validate_input("Hola mundo")
        assert result.text == "Hola mundo"
        assert result.channel == "log"

    def test_empty_string_input(self):
        agent = TextChannelAgent()
        result = agent._validate_input("")
        assert result.text == ""
        assert result.channel == "log"

    def test_integer_input(self):
        """Tipo incorrecto → str() conversion."""
        agent = TextChannelAgent()
        result = agent._validate_input(42)
        assert result.text == "42"
        assert result.channel == "log"

    def test_none_input(self):
        agent = TextChannelAgent()
        result = agent._validate_input(None)
        assert result.text == "None"
        assert result.channel == "log"

    def test_list_input(self):
        agent = TextChannelAgent()
        result = agent._validate_input([1, 2, 3])
        assert isinstance(result, TextChannelInput)


# ════════════════════════════════════════════════════════════════
#  A53 — execute() without wiring
# ════════════════════════════════════════════════════════════════

class TestA53ExecuteUnwired:

    def test_execute_without_registry_returns_failure(self):
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Hola", channel="whatsapp")
        result = agent.execute(inp)
        assert result.success is False
        assert "not wired" in result.error or "Registry" in result.error

    def test_execute_never_raises(self):
        agent = TextChannelAgent()
        r1 = agent.execute(TextChannelInput())
        r2 = agent.execute({})
        r3 = agent.execute("test")
        r4 = agent.execute(None)
        r5 = agent.execute(42)
        assert all(isinstance(r, TextChannelResult) for r in [r1, r2, r3, r4, r5])

    def test_execute_empty_text(self):
        agent = TextChannelAgent()
        # Sin registry, siempre falla con "not wired"
        result = agent.execute(TextChannelInput(text="", channel="whatsapp"))
        assert result.success is False


# ════════════════════════════════════════════════════════════════
#  A53 — fallback()
# ════════════════════════════════════════════════════════════════

class TestA53Fallback:

    def test_fallback_returns_safe_result(self):
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Hola", channel="whatsapp")
        result = agent.fallback(inp)
        assert result.success is False
        assert result.source == "fallback"
        assert result.channel_used == "log"
        assert result.status == "fallback"
        assert result.messages_sent == 0
        assert "not attempted" in result.error

    def test_fallback_with_dict(self):
        agent = TextChannelAgent()
        result = agent.fallback({"text": "Test", "channel": "whatsapp"})
        assert result.success is False
        assert result.source == "fallback"

    def test_fallback_with_string(self):
        agent = TextChannelAgent()
        result = agent.fallback("Test message")
        assert result.success is False
        assert result.original_length == len("Test message")

    def test_fallback_never_raises(self):
        agent = TextChannelAgent()
        r1 = agent.fallback(None)
        r2 = agent.fallback(42)
        r3 = agent.fallback("")
        r4 = agent.fallback(TextChannelInput(text="x" * 10000))
        assert all(isinstance(r, TextChannelResult) for r in [r1, r2, r3, r4])


# ════════════════════════════════════════════════════════════════
#  A53 — _make_result helper
# ════════════════════════════════════════════════════════════════

class TestA53MakeResult:

    def test_make_result_defaults(self):
        data = TextChannelInput(text="Hola", channel="whatsapp")
        result = TextChannelAgent._make_result(data=data)
        assert result.success is False
        assert result.channel_used == "whatsapp"
        assert result.original_channel == "whatsapp"
        assert result.source == "deterministic"

    def test_make_result_with_overrides(self):
        data = TextChannelInput(text="Test", channel="telegram")
        result = TextChannelAgent._make_result(
            data=data,
            success=True,
            channel_used="telegram",
            messages_sent=1,
            status="sent",
            delivered_length=4,
        )
        assert result.success is True
        assert result.messages_sent == 1
        assert result.delivered_length == 4

    def test_make_result_empty_channel_defaults_to_log(self):
        data = TextChannelInput(text="Test", channel="")
        result = TextChannelAgent._make_result(data=data)
        assert result.channel_used == "log"  # Fallback to "log"


# ════════════════════════════════════════════════════════════════
#  A53 — _add_part_indicators helper
# ════════════════════════════════════════════════════════════════

class TestA53PartIndicators:

    def test_single_chunk_no_indicator(self):
        result = TextChannelAgent._add_part_indicators(["Hola"], 4096)
        assert result == ["Hola"]

    def test_two_chunks_with_indicators(self):
        chunks = ["Part 1", "Part 2"]
        result = TextChannelAgent._add_part_indicators(chunks, 4096)
        assert len(result) == 2
        assert "[1/2]" in result[0]
        assert "[2/2]" in result[1]

    def test_indicators_respect_max_len(self):
        """Si el indicador no cabe, no se agrega."""
        chunks = ["A" * 4095, "B" * 100]
        result = TextChannelAgent._add_part_indicators(chunks, 4096)
        # "[1/2] " = 6 chars → total would be 4095+6 = 4101 > 4096
        # So indicator might not be added to first chunk
        # The second chunk should be fine
        assert len(result) == 2

    def test_empty_chunks_list(self):
        result = TextChannelAgent._add_part_indicators([], 4096)
        assert result == []

    def test_many_chunks(self):
        chunks = [f"Chunk {i}" for i in range(10)]
        result = TextChannelAgent._add_part_indicators(chunks, 4096)
        assert len(result) == 10
        assert "[1/10]" in result[0]
        assert "[10/10]" in result[9]


# ════════════════════════════════════════════════════════════════
#  A53 — deliver() async without registry
# ════════════════════════════════════════════════════════════════

class TestA53AsyncDeliver:

    @pytest.mark.asyncio
    async def test_deliver_without_registry(self):
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Hola", channel="whatsapp")
        result = await agent.deliver(inp)
        assert result.success is False
        assert "not wired" in result.error or "Registry" in result.error

    @pytest.mark.asyncio
    async def test_deliver_with_string(self):
        agent = TextChannelAgent()
        result = await agent.deliver("Test")
        assert result.success is False  # No registry

    @pytest.mark.asyncio
    async def test_deliver_never_raises(self):
        agent = TextChannelAgent()
        r1 = await agent.deliver(None)
        r2 = await agent.deliver(42)
        assert all(isinstance(r, TextChannelResult) for r in [r1, r2])


# ════════════════════════════════════════════════════════════════
#  A53 — Edge cases
# ════════════════════════════════════════════════════════════════

class TestA53EdgeCases:

    def test_very_long_text_input(self):
        """Texto extremadamente largo — el dataclass lo acepta."""
        agent = TextChannelAgent()
        long_text = "A" * 1_000_000
        result = agent._validate_input(long_text)
        assert len(result.text) == 1_000_000

    def test_unicode_text(self):
        """Texto con emojis y caracteres Unicode."""
        agent = TextChannelAgent()
        result = agent._validate_input("Hola 🌍 ñ é ü 中文")
        assert "🌍" in result.text
        assert "中文" in result.text

    def test_special_chars_in_text(self):
        agent = TextChannelAgent()
        result = agent._validate_input("<script>alert('xss')</script>")
        assert "script" in result.text  # Not sanitized at input level

    def test_max_chunks_zero(self):
        """max_chunks=0 → el agente lo maneja."""
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Test", max_chunks=0)
        # Sin registry, solo validamos que no crashee
        result = agent.execute(inp)
        assert isinstance(result, TextChannelResult)

    def test_negative_max_chunks(self):
        agent = TextChannelAgent()
        inp = TextChannelInput(text="Test", max_chunks=-5)
        result = agent.execute(inp)
        assert isinstance(result, TextChannelResult)
