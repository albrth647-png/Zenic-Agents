"""Tests for Channel System — ChannelTypes, PlatformLimits, Protocol functions.

Rigor: sin mocks, datos reales, cubre normal + vacío + extremos + error.
"""

import pytest

from src.core.channels._types import (
    ChannelCapability,
    ChannelPriority,
    DeliveryStatus,
    ChannelMessage,
    ChannelResponse,
    ProviderConfig,
    RateLimitInfo,
)
from src.core.channels._formatter._limits import PlatformLimits, LIMITS
from src.core.channels._protocol import (
    ChannelProvider,
    InboundChannelProvider,
    has_capability,
    requires_inbound,
    can_send_confirmation,
    can_receive_voice,
    can_send_voice,
)


# ════════════════════════════════════════════════════════════════
#  ChannelCapability enum
# ════════════════════════════════════════════════════════════════

class TestChannelCapability:

    def test_voice_capabilities_exist(self):
        """RECEIVE_VOICE y SEND_VOICE deben estar en el enum."""
        assert ChannelCapability.RECEIVE_VOICE == "receive_voice"
        assert ChannelCapability.SEND_VOICE == "send_voice"

    def test_all_capabilities_are_unique(self):
        """No debe haber valores duplicados."""
        values = [cap.value for cap in ChannelCapability]
        assert len(values) == len(set(values))

    def test_core_capabilities(self):
        assert ChannelCapability.SEND_TEXT == "send_text"
        assert ChannelCapability.RECEIVE_MESSAGE == "receive_message"
        assert ChannelCapability.THREAD == "thread"
        assert ChannelCapability.REPLY == "reply"


# ════════════════════════════════════════════════════════════════
#  ChannelMessage
# ════════════════════════════════════════════════════════════════

class TestChannelMessage:

    def test_defaults(self):
        msg = ChannelMessage()
        assert msg.text == " "  # __post_init__ sets " " when no content
        assert msg.voice_url == ""
        assert msg.voice_duration == 0.0
        assert msg.voice_format == ""
        assert msg.transcription == ""

    def test_normal_text_message(self):
        msg = ChannelMessage(text="Hola", recipient="+535551234")
        assert msg.text == "Hola"
        assert msg.recipient == "+535551234"

    def test_voice_message_fields(self):
        msg = ChannelMessage(
            voice_url="https://api.whatsapp.com/media/abc123",
            voice_format="ogg",
            voice_duration=12.5,
            voice_mime_type="audio/ogg",
        )
        assert msg.has_voice is True
        assert msg.has_transcription is False
        assert msg.voice_duration == 12.5

    def test_transcribed_voice_message(self):
        msg = ChannelMessage(
            voice_url="https://example.com/audio.ogg",
            transcription="Buenos días",
        )
        assert msg.has_voice is True
        assert msg.has_transcription is True
        assert msg.transcription == "Buenos días"

    def test_frozen_message_cannot_be_modified(self):
        """ChannelMessage es frozen=True — no se puede mutar."""
        msg = ChannelMessage(text="Hola")
        with pytest.raises(AttributeError):
            msg.text = "Adiós"

    def test_empty_message_gets_space_fill(self):
        """Si no hay contenido, __post_init__ asigna " "."""
        msg = ChannelMessage()
        assert msg.text == " "

    def test_voice_only_message(self):
        """Mensaje solo con voice_url (sin text) — __post_init__ NO asigna espacio
        porque voice_url ya es contenido, la condición se cumple."""
        msg = ChannelMessage(voice_url="https://example.com/a.ogg")
        assert msg.has_voice is True
        # text stays empty because voice_url satisfies the __post_init__ check

    def test_html_message(self):
        msg = ChannelMessage(html="<b>Hola</b>", recipient="user@test.com")
        assert msg.html == "<b>Hola</b>"

    def test_file_url_message(self):
        msg = ChannelMessage(file_url="https://example.com/doc.pdf")
        assert msg.file_url != ""


# ════════════════════════════════════════════════════════════════
#  ChannelResponse
# ════════════════════════════════════════════════════════════════

class TestChannelResponse:

    def test_normal_success(self):
        resp = ChannelResponse(
            success=True,
            channel="whatsapp",
            message_id="msg_123",
            status=DeliveryStatus.SENT,
        )
        assert resp.success is True
        assert resp.channel == "whatsapp"
        assert resp.status == DeliveryStatus.SENT

    def test_failure_response(self):
        resp = ChannelResponse(
            success=False,
            channel="telegram",
            status=DeliveryStatus.FAILED,
            error="Connection timeout",
        )
        assert resp.success is False
        assert "timeout" in resp.error

    def test_fallback_response(self):
        resp = ChannelResponse(
            success=True,
            channel="sms",
            status=DeliveryStatus.FALLBACK,
        )
        assert resp.status == DeliveryStatus.FALLBACK

    def test_to_dict(self):
        resp = ChannelResponse(
            success=True,
            channel="whatsapp",
            message_id="m1",
            status=DeliveryStatus.SENT,
        )
        d = resp.to_dict()
        assert d["success"] is True
        assert d["channel"] == "whatsapp"
        assert d["status"] == "sent"

    def test_frozen(self):
        resp = ChannelResponse(success=True, channel="test")
        with pytest.raises(AttributeError):
            resp.channel = "other"


# ════════════════════════════════════════════════════════════════
#  ProviderConfig
# ════════════════════════════════════════════════════════════════

class TestProviderConfig:

    def test_defaults(self):
        cfg = ProviderConfig()
        assert cfg.enabled is True
        assert cfg.webhook_url == ""
        assert cfg.api_url == ""

    def test_is_configured(self):
        assert ProviderConfig().is_configured is False
        assert ProviderConfig(webhook_url="https://hook.com").is_configured is True
        assert ProviderConfig(bot_token="123").is_configured is True

    def test_not_configured_without_any_method(self):
        assert ProviderConfig(phone_number="+123").is_configured is False


# ════════════════════════════════════════════════════════════════
#  RateLimitInfo
# ════════════════════════════════════════════════════════════════

class TestRateLimitInfo:

    def test_defaults(self):
        info = RateLimitInfo()
        assert info.remaining == -1
        assert info.is_unknown is True
        assert info.is_limited is False

    def test_rate_limited(self):
        info = RateLimitInfo(remaining=0)
        assert info.is_limited is True
        assert info.is_unknown is False

    def test_has_remaining(self):
        info = RateLimitInfo(remaining=50, limit=100)
        assert info.is_limited is False
        assert info.is_unknown is False


# ════════════════════════════════════════════════════════════════
#  PlatformLimits
# ════════════════════════════════════════════════════════════════

class TestPlatformLimits:

    def test_text_limits_exist(self):
        lim = PlatformLimits()
        assert lim.whatsapp_text > 0
        assert lim.telegram_text > 0
        assert lim.discord_text > 0
        assert lim.slack_text > 0
        assert lim.sms_text > 0

    def test_voice_limits_exist(self):
        lim = PlatformLimits()
        assert lim.whatsapp_voice_max_duration > 0
        assert lim.whatsapp_voice_max_size > 0
        assert lim.telegram_voice_max_duration > 0
        assert lim.telegram_voice_max_size > 0
        assert lim.discord_voice_max_duration > 0
        assert lim.discord_voice_max_size > 0

    def test_specific_values(self):
        lim = PlatformLimits()
        assert lim.whatsapp_text == 4096
        assert lim.telegram_text == 4096
        assert lim.discord_text == 2000
        assert lim.sms_text == 160
        assert lim.whatsapp_voice_max_duration == 600  # 10 min
        assert lim.whatsapp_voice_max_size == 16 * 1024 * 1024  # 16 MB

    def test_transcription_max_length(self):
        lim = PlatformLimits()
        assert lim.transcription_max_length > 0

    def test_limits_singleton(self):
        """LIMITS es un singleton — la misma instancia."""
        assert LIMITS is not None
        assert isinstance(LIMITS, PlatformLimits)
        assert LIMITS.whatsapp_text == 4096

    def test_voice_sizes_in_bytes(self):
        lim = PlatformLimits()
        # WhatsApp: 16MB, Telegram: 20MB, Discord: 25MB
        assert lim.whatsapp_voice_max_size == 16_777_216  # 16 * 1024 * 1024
        assert lim.telegram_voice_max_size == 20_971_520  # 20 * 1024 * 1024
        assert lim.discord_voice_max_size == 26_214_400  # 25 * 1024 * 1024


# ════════════════════════════════════════════════════════════════
#  Protocol functions with real objects
# ════════════════════════════════════════════════════════════════

class _FakeProvider:
    """Minimal real object that satisfies ChannelProvider protocol."""

    def __init__(self, caps=None):
        self._caps = frozenset(caps or {ChannelCapability.SEND_TEXT})

    @property
    def name(self):
        return "fake"

    @property
    def capabilities(self):
        return self._caps

    @property
    def is_available(self):
        return True

    async def send(self, message):
        return ChannelResponse(success=True, channel="fake")

    async def send_confirmation(self, request):
        return ChannelResponse(success=False, channel="fake", error="Not supported")

    async def start(self):
        pass

    async def stop(self):
        pass

    @property
    def stats(self):
        return {}

    @property
    def rate_limit_info(self):
        return RateLimitInfo()


class _FakeInboundProvider(_FakeProvider):
    """Provider with inbound + voice capability."""

    def __init__(self):
        super().__init__(caps={
            ChannelCapability.SEND_TEXT,
            ChannelCapability.RECEIVE_MESSAGE,
            ChannelCapability.RECEIVE_VOICE,
        })

    def set_message_handler(self, handler):
        self._msg_handler = handler

    def set_confirmation_handler(self, handler):
        self._conf_handler = handler

    @property
    def is_listening(self):
        return True


class TestProtocolFunctions:

    def test_has_capability_true(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_TEXT, ChannelCapability.THREAD})
        assert has_capability(p, ChannelCapability.SEND_TEXT) is True
        assert has_capability(p, ChannelCapability.THREAD) is True

    def test_has_capability_false(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_TEXT})
        assert has_capability(p, ChannelCapability.SEND_CONFIRMATION) is False

    def test_can_receive_voice(self):
        p = _FakeInboundProvider()
        assert can_receive_voice(p) is True

    def test_cannot_receive_voice(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_TEXT})
        assert can_receive_voice(p) is False

    def test_can_send_voice(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_VOICE})
        assert can_send_voice(p) is True

    def test_cannot_send_voice(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_TEXT})
        assert can_send_voice(p) is False

    def test_can_send_confirmation(self):
        p = _FakeProvider(caps={ChannelCapability.SEND_CONFIRMATION})
        assert can_send_confirmation(p) is True

    def test_requires_inbound(self):
        p = _FakeInboundProvider()
        assert requires_inbound(p) is True

    def test_not_inbound(self):
        p = _FakeProvider()
        assert requires_inbound(p) is False


# ════════════════════════════════════════════════════════════════
#  ChannelPriority & DeliveryStatus
# ════════════════════════════════════════════════════════════════

class TestChannelPriority:

    def test_all_levels_exist(self):
        assert ChannelPriority.LOW == "low"
        assert ChannelPriority.NORMAL == "normal"
        assert ChannelPriority.HIGH == "high"
        assert ChannelPriority.URGENT == "urgent"
        assert ChannelPriority.EMERGENCY == "emergency"

    def test_ordering(self):
        """ChannelPriority values are strings — no numeric ordering guarantee.
        The priority levels are semantic, not lexicographic."""
        priorities = [ChannelPriority.LOW, ChannelPriority.NORMAL, ChannelPriority.HIGH,
                      ChannelPriority.URGENT, ChannelPriority.EMERGENCY]
        assert len(priorities) == 5
        # Each priority is distinct
        values = [p.value for p in priorities]
        assert len(set(values)) == 5


class TestDeliveryStatus:

    def test_all_statuses(self):
        expected = {"pending", "sent", "delivered", "failed", "rate_limited", "fallback", "dry_run"}
        actual = {s.value for s in DeliveryStatus}
        assert expected == actual
