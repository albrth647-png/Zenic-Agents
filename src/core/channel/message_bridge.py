"""MessageBridge — Conecta canales con el motor de procesamiento.

Flujo reactivo:
    Canal (WhatsApp/Telegram) → A52/A53 → Engine → A53 deliver → Canal response

Flujo proactivo:
    SNA/Autopilot → ProactiveChannelBridge → A53 deliver → Canal

El bridge es el "cable" que conecta todo.
"""

from __future__ import annotations

import logging
from typing import Any, Callable
from enum import Enum

from src.core.channel.a52_voice import VoiceChannelAgent, VoiceMessage, VoiceResult
from src.core.channel.a53_text import TextChannelAgent, TextMessage, TextResult, ChannelType

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    DOCUMENT = "document"


class MessageBridge:
    """Bridge entre canales y el motor de procesamiento.

    Recibe mensajes de canales, los procesa con A52/A53,
    y devuelve la respuesta por el canal correspondiente.
    """

    def __init__(
        self,
        voice_agent: VoiceChannelAgent | None = None,
        text_agent: TextChannelAgent | None = None,
        on_text_processed: Callable[[str, str, str], str | None] | None = None,
    ):
        self.voice_agent = voice_agent or VoiceChannelAgent()
        self.text_agent = text_agent or TextChannelAgent()
        self._on_text_processed = on_text_processed

        # Registro de canales activos
        self._active_channels: dict[str, ChannelType] = {}

        logger.info("MessageBridge inicializado")

    def register_channel(self, channel_id: str, channel_type: ChannelType):
        """Registra un canal activo."""
        self._active_channels[channel_id] = channel_type
        logger.info(f"Canal registrado: {channel_id} → {channel_type.value}")

    def handle_text(self, channel: str, sender: str, text: str) -> TextResult:
        """Maneja un mensaje de texto entrante."""
        channel_type = self._active_channels.get(channel, ChannelType.WEB)

        message = TextMessage(
            channel=channel_type,
            recipient=sender,
            text=text,
            sender=sender,
            is_proactive=False,
        )

        # Procesar con A53
        result = self.text_agent.process(message)

        # Si hay callback de procesamiento, ejecutarlo
        if self._on_text_processed and result.success:
            response = self._on_text_processed(text, sender, channel)
            if response:
                # Enviar respuesta por el canal
                response_msg = TextMessage(
                    channel=channel_type,
                    recipient=sender,
                    text=response,
                    is_proactive=False,
                )
                self.text_agent.process(response_msg)

        return result

    def handle_voice(self, channel: str, sender: str, file_url: str, file_format: str = "ogg") -> VoiceResult:
        """Maneja un mensaje de voz entrante."""
        from src.core.channel.a52_voice import VoiceFormat

        voice = VoiceMessage(
            channel=channel,
            sender=sender,
            file_url=file_url,
            file_format=VoiceFormat(file_format),
        )

        # Procesar con A52 → obtiene texto
        voice_result = self.voice_agent.process(voice)

        if voice_result.success and voice_result.text:
            # El texto transcrito va al motor como un mensaje de texto normal
            self.handle_text(channel, sender, voice_result.text)

        return voice_result

    def send_proactive_message(self, channel_type: ChannelType, recipient: str, text: str) -> TextResult:
        """Envía un mensaje proactivo (desde SNA/Autopilot) al usuario."""
        message = TextMessage(
            channel=channel_type,
            recipient=recipient,
            text=text,
            is_proactive=True,
        )
        return self.text_agent.process(message)

    def get_active_channels(self) -> dict[str, str]:
        """Retorna canales activos."""
        return {k: v.value for k, v in self._active_channels.items()}
