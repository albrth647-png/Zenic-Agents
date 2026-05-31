"""A52 VoiceChannelAgent — Pipeline de voz a texto.

Flujo: download→validate→convert→transcribe→deliver text

No usa IA para transcribir — usa whisper local o servicio determinista.
La IA solo se usa en el SafetyGate para aprobar/rechazar el resultado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VoiceFormat(str, Enum):
    OGG = "ogg"
    MP3 = "mp3"
    WAV = "wav"
    WEBM = "webm"
    M4A = "m4a"


@dataclass
class VoiceMessage:
    """Mensaje de voz entrante."""

    channel: str  # "whatsapp", "telegram"
    sender: str
    file_url: str
    file_format: VoiceFormat = VoiceFormat.OGG
    duration_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceResult:
    """Resultado del pipeline de voz."""

    success: bool
    text: str = ""
    language: str = ""
    confidence: float = 0.0
    error: str = ""
    original: VoiceMessage | None = None


class VoiceChannelAgent:
    """A52 — Pipeline de procesamiento de mensajes de voz.

    download → validate → convert → transcribe → deliver text

    Cada paso es determinista. No hay IA en el pipeline.
    La IA solo evalúa el resultado final en el SafetyGate.
    """

    # Límites
    MAX_FILE_SIZE_MB = 25
    MAX_DURATION_SECONDS = 300  # 5 minutos
    SUPPORTED_FORMATS = {VoiceFormat.OGG, VoiceFormat.MP3, VoiceFormat.WAV, VoiceFormat.WEBM, VoiceFormat.M4A}  # noqa: RUF012

    def __init__(self, temp_dir: str = "/tmp/zenic_voice"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("A52 VoiceChannelAgent inicializado")

    def process(self, voice: VoiceMessage) -> VoiceResult:
        """Pipeline completo: download→validate→convert→transcribe→deliver."""
        try:
            # Step 1: Validate
            self._validate(voice)

            # Step 2: Download
            local_path = self._download(voice)

            # Step 3: Convert
            wav_path = self._convert(local_path)

            # Step 4: Transcribe
            text, language, confidence = self._transcribe(wav_path)

            # Step 5: Cleanup
            self._cleanup(local_path, wav_path)

            return VoiceResult(
                success=True,
                text=text,
                language=language,
                confidence=confidence,
                original=voice,
            )

        except Exception as e:
            logger.error(f"A52 error procesando voz: {e}")
            return VoiceResult(
                success=False,
                error=str(e),
                original=voice,
            )

    def _validate(self, voice: VoiceMessage):
        """Valida el mensaje de voz antes de procesar."""
        if voice.file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato no soportado: {voice.file_format}. Soportados: {self.SUPPORTED_FORMATS}")

        if voice.duration_seconds > self.MAX_DURATION_SECONDS:
            raise ValueError(f"Audio muy largo: {voice.duration_seconds}s (máximo: {self.MAX_DURATION_SECONDS}s)")

        if not voice.file_url:
            raise ValueError("URL de archivo vacía")

    def _download(self, voice: VoiceMessage) -> Path:
        """Descarga el archivo de audio. Retorna path local."""
        # En producción, descargar de la URL del canal
        # Por ahora, si es un path local, usarlo directamente
        if voice.file_url.startswith("/"):
            return Path(voice.file_url)

        # Simular descarga — en producción usar httpx/aiohttp
        filename = f"voice_{voice.channel}_{voice.sender}_{id(voice)}.{voice.file_format.value}"
        local_path = self.temp_dir / filename
        logger.debug(f"Download simulado: {voice.file_url} → {local_path}")
        return local_path

    def _convert(self, input_path: Path) -> Path:
        """Convierte audio a WAV para transcripción."""
        if input_path.suffix == ".wav":
            return input_path

        wav_path = input_path.with_suffix(".wav")

        # En producción, usar ffmpeg para convertir
        # ffmpeg -i input.ogg -ar 16000 -ac 1 output.wav
        logger.debug(f"Conversión simulada: {input_path} → {wav_path}")
        return wav_path

    def _transcribe(self, wav_path: Path) -> tuple[str, str, float]:
        """Transcribe audio a texto usando whisper local o servicio determinista."""
        # En producción, usar:
        # 1. whisper local
        # 2. O servicio de transcripción determinista
        # Por ahora, placeholder que indica que necesita implementación real

        if not wav_path.exists():
            return ("[Audio recibido - transcripción pendiente]", "es", 0.0)

        logger.debug(f"Transcripción de: {wav_path}")
        return ("[Transcripción pendiente de implementación]", "es", 0.5)

    def _cleanup(self, *paths: Path):
        """Limpia archivos temporales."""
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
