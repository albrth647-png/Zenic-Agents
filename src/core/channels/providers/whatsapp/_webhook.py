"""
ZENIC-AGENTS — WhatsApp Business Channel Provider — Webhook Module

Inbound:  Webhook callbacks with HMAC-SHA256 signature verification
Supports:
  - Webhook subscription verification (Meta GET handshake)
  - HMAC-SHA256 payload signature verification
  - Inbound message parsing (text, interactive replies, audio/voice)
  - Message and confirmation handler registration
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from ..._types import (
    ChannelMessage,
    ConfirmationHandler,
    MessageHandler,
)

logger = logging.getLogger("zenic_agents.channels.whatsapp")

# ──────────────────────────────────────────────────────────────
#  WHATSAPP VOICE MESSAGE FORMAT MAPPING
# ──────────────────────────────────────────────────────────────

# WhatsApp audio.mime_type → normalized voice_format
_WHATSAPP_MIME_TO_FORMAT: Dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/ogg; codecs=opus": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/amr": "amr",
    "audio/aac": "aac",
}


class WhatsAppWebhookMixin:
    """Mixin providing WhatsApp webhook and inbound message functionality.

    Intended to be mixed into WhatsAppChannelProviderBase to form
    the complete WhatsAppChannelProvider.
    """

    # ── InboundChannelProvider Protocol ─────────────────────────

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Register a handler for incoming WhatsApp messages."""
        self._message_handler: Optional[MessageHandler] = handler  # type: ignore[attr-defined]
        logger.debug("WhatsAppChannelProvider: message handler registered")

    def set_confirmation_handler(self, handler: ConfirmationHandler) -> None:
        """Register a handler for button callback responses."""
        self._confirmation_handler: Optional[ConfirmationHandler] = handler  # type: ignore[attr-defined]
        logger.debug("WhatsAppChannelProvider: confirmation handler registered")

    @property
    def is_listening(self) -> bool:
        """Whether the provider is actively listening."""
        return self._started and self.is_available  # type: ignore[attr-defined]

    # ── Webhook Verification ────────────────────────────────────

    def verify_webhook(self, mode: str, token: str) -> bool:
        """Verify WhatsApp webhook subscription request.

        Called during GET /webhook verification by Meta.

        Args:
            mode: hub.mode (must be "subscribe")
            token: hub.verify_token (must match configured verify_token)

        Returns:
            True if verification succeeds, False otherwise.
        """
        if not self._verify_token:  # type: ignore[attr-defined]
            logger.warning("WhatsAppChannelProvider: no verify token configured")
            return False

        return mode == "subscribe" and token == self._verify_token  # type: ignore[attr-defined]

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify WhatsApp webhook payload signature (HMAC-SHA256).

        Args:
            payload: Raw request body bytes.
            signature: X-Hub-Signature-256 header value.

        Returns:
            True if signature is valid, False otherwise.
        """
        if not self._app_secret:  # type: ignore[attr-defined]
            logger.warning("WhatsAppChannelProvider: no app secret configured")
            return False

        if not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self._app_secret.encode("utf-8"),  # type: ignore[attr-defined]
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare(expected, signature[7:])

    def parse_inbound_message(self, payload: Dict[str, Any]) -> Optional[ChannelMessage]:
        """Parse a WhatsApp webhook payload into a ChannelMessage.

        Supports:
          - Text messages
          - Interactive button/list replies
          - Audio/voice messages (populates voice_url, voice_format, etc.)
          - Document/image messages (as file attachments)

        Args:
            payload: Parsed JSON body from webhook POST.

        Returns:
            ChannelMessage if valid, None if not a message event.
        """
        try:
            entry = payload.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value = change.get("value", {})

            # Skip status updates
            if "statuses" in value:
                return None

            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            msg_type = msg.get("type", "text")
            phone_number = msg.get("from", "")
            msg_id = msg.get("id", "")

            # ── Parse by message type ──
            text = ""
            voice_url = ""
            voice_duration = 0.0
            voice_format = ""
            voice_mime_type = ""

            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")

            elif msg_type == "audio":
                # WhatsApp voice/audio message
                audio_data = msg.get("audio", {})
                voice_url = audio_data.get("id", "")  # Media ID → needs download via API
                voice_duration = float(audio_data.get("duration", 0))
                voice_mime_type = audio_data.get("mime_type", "audio/ogg")
                voice_format = _WHATSAPP_MIME_TO_FORMAT.get(
                    voice_mime_type,
                    voice_mime_type.split("/")[-1] if "/" in voice_mime_type else "ogg",
                )
                # WhatsApp voice messages may have a transcript field
                text = audio_data.get("transcript", "")

            elif msg_type == "voice":
                # Some API versions use "voice" instead of "audio" for voice notes
                voice_data = msg.get("voice", {})
                voice_url = voice_data.get("id", "")
                voice_duration = float(voice_data.get("duration", 0))
                voice_mime_type = voice_data.get("mime_type", "audio/ogg; codecs=opus")
                voice_format = _WHATSAPP_MIME_TO_FORMAT.get(
                    voice_mime_type, "ogg",
                )
                text = voice_data.get("transcript", "")

            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                interactive_type = interactive.get("type", "")
                if interactive_type == "button_reply":
                    text = interactive.get("button_reply", {}).get("title", "")
                elif interactive_type == "list_reply":
                    text = interactive.get("list_reply", {}).get("title", "")

            elif msg_type == "document":
                # Document messages — treat as file attachment
                doc_data = msg.get("document", {})
                text = doc_data.get("caption", "")

            elif msg_type == "image":
                # Image messages — treat as file attachment
                img_data = msg.get("image", {})
                text = img_data.get("caption", "")

            # ── Build metadata ──
            metadata: Dict[str, Any] = {
                "whatsapp_message_id": msg_id,
                "whatsapp_type": msg_type,
                "from_phone": phone_number,
            }

            # Add audio-specific metadata
            if voice_url:
                metadata["whatsapp_media_id"] = voice_url
                metadata["voice_needs_download"] = True  # Indicates URL is a media ID

            return ChannelMessage(
                text=text,
                recipient=phone_number,
                reply_to=msg_id,
                voice_url=voice_url,
                voice_duration=voice_duration,
                voice_format=voice_format,
                voice_mime_type=voice_mime_type,
                metadata=metadata,
            )
        except (IndexError, KeyError, TypeError) as e:
            logger.warning("WhatsAppChannelProvider: failed to parse inbound: %s", e)
            return None


__all__ = ["WhatsAppWebhookMixin"]
