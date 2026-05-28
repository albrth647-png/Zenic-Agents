"""Ear — Speech-to-Text (STT) Service for VoicePipeline.

SINGLE RESPONSIBILITY: Convert audio bytes → transcription text.

The Ear service is the ONLY entry point for audio transcription in
Zenic-Agents. It uses the Strategy Pattern to support multiple STT
backends with automatic detection and fallback.

Design invariants:
  1. NEVER raises — all errors captured in TranscriptionResult.
  2. INBOUND ONLY — audio → text. No TTS capability exists here.
  3. Core system NEVER knows if input came as text or voice.
  4. Thread-safe — multiple concurrent transcriptions are safe.
  5. Backend-agnostic — new backends plug in via STTBackend protocol.
  6. Auto-detection — picks the best available backend at startup.
  7. Zero bloat — backends are lazy-loaded; missing deps are handled.

Fallback chain (by default):
  1. faster_whisper — best local STT (CTranslate2, CPU-friendly)
  2. whisper — Whisper local (PyTorch, heavier)
  3. dummy — Always available, returns empty transcription

Usage:
    ear = Ear()                              # Auto-detect best backend
    result = ear.transcribe(audio_bytes, "ogg")  # Transcribe
    if result.success:
        print(result.transcribed_text)       # "Hola, necesito ayuda..."
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ._types import (
    STTBackendConfig,
    TranscriptionResult,
    VoicePipelineMetrics,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_logger = logging.getLogger("zenic_agents.voice_pipeline.ear")


# ──────────────────────────────────────────────────────────────
#  STT BACKEND PROTOCOL (Strategy Pattern)
# ──────────────────────────────────────────────────────────────


class STTBackend(ABC):
    """Abstract base class for Speech-to-Text backends.

    Every STT backend must implement this interface.
    The Ear service uses these backends via Strategy Pattern —
    the active backend is selected at runtime based on
    availability and configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique backend identifier (e.g. 'whisper', 'cloud')."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this backend can be used right now.

        Returns False if:
          - Required library not installed
          - API key not configured
          - Model not downloaded
          - Service unreachable
        """
        ...

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text (synchronous).

        Args:
            audio_bytes: Raw audio data (any supported format).
            audio_format: Hint about the audio format (e.g. "ogg", "mp3").
            language: Hint about the spoken language (e.g. "es", "en").
                     Empty string = auto-detect.

        Returns:
            TranscriptionResult — NEVER raises.
        """
        ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return backend health status for monitoring."""
        ...


# ──────────────────────────────────────────────────────────────
#  DUMMY BACKEND — Always available, zero deps
# ──────────────────────────────────────────────────────────────


class DummyBackend(STTBackend):
    """Dummy STT backend — always available, returns empty result.

    Used for:
      - Testing and development
      - Fallback when no real STT backend is available
      - Dry-run mode

    This backend NEVER produces transcription text.
    It always returns success=False with an informative error.
    """

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def is_available(self) -> bool:
        return True  # Always available — zero dependencies

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Return empty transcription result.

        The dummy backend logs the audio size for debugging
        but does NOT attempt transcription.
        """
        audio_size = len(audio_bytes) if audio_bytes else 0
        _logger.debug(
            "DummyBackend: skipping transcription (audio_size=%d, format=%s)",
            audio_size,
            audio_format or "unknown",
        )
        return TranscriptionResult(
            success=False,
            transcribed_text="",
            confidence=0.0,
            language=language,
            audio_format=audio_format,
            backend="dummy",
            error="Dummy backend — no STT engine configured. "
            "Install whisper, faster-whisper, or configure a cloud API.",
            source="dummy",
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "backend": "dummy",
            "available": True,
            "note": "No real STT backend — transcription disabled",
        }


# ──────────────────────────────────────────────────────────────
#  FASTER-WHISPER BACKEND — Best local STT (CTranslate2)
# ──────────────────────────────────────────────────────────────


class FasterWhisperBackend(STTBackend):
    """STT backend using faster-whisper (CTranslate2-based).

    Faster-whisper is 4x faster than Whisper local with the same
    accuracy. It uses CTranslate2 for efficient CPU/GPU inference.

    Requirements:
      pip install faster-whisper

    Configuration:
      - model_size: tiny|base|small|medium|large-v2|large-v3
      - device: cpu|cuda
      - compute_type: int8|float16|int8_float16
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model: Any | None = None
        self._load_error: str = ""

    @property
    def name(self) -> str:
        return "faster_whisper"

    @property
    def is_available(self) -> bool:
        """Check if faster-whisper is importable."""
        try:
            import faster_whisper  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_model(self) -> Any:
        """Lazy-load the faster-whisper model (once)."""
        if self._model is not None:
            return self._model

        if self._load_error:
            return None

        try:
            from faster_whisper import WhisperModel

            _logger.info(
                "FasterWhisperBackend: loading model=%s device=%s compute=%s",
                self._model_size,
                self._device,
                self._compute_type,
            )
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            _logger.info("FasterWhisperBackend: model loaded successfully")
            return self._model
        except Exception as e:
            self._load_error = str(e)
            _logger.error("FasterWhisperBackend: model load failed: %s", e)
            return None

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Transcribe using faster-whisper."""
        start = time.monotonic()

        if not audio_bytes:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="faster_whisper",
                error="Empty audio bytes",
                source="faster_whisper",
            )

        model = self._ensure_model()
        if model is None:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="faster_whisper",
                error=f"Model not loaded: {self._load_error}",
                source="faster_whisper",
            )

        try:
            # faster-whisper can read from a numpy array or file path
            # We write to a temp file for format compatibility
            import os
            import tempfile

            ext = audio_format if audio_format else "wav"
            suffix = f".{ext}" if not ext.startswith(".") else ext

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                lang = language or self._language or None
                segments, info = model.transcribe(
                    tmp_path,
                    language=lang,
                    beam_size=5,
                    vad_filter=True,  # Voice Activity Detection
                    vad_parameters={
                        "min_silence_duration_ms": 500,
                    },
                )

                # Collect all segments
                text_parts: list[str] = []
                total_confidence = 0.0
                segment_count = 0

                for segment in segments:
                    text_parts.append(segment.text.strip())
                    total_confidence += segment.avg_logprob
                    segment_count += 1

                transcribed = " ".join(text_parts)
                avg_confidence = (
                    min(1.0, max(0.0, (total_confidence / segment_count + 1.0) / 2.0)) if segment_count > 0 else 0.0
                )

                duration = time.monotonic() - start
                _logger.info(
                    "FasterWhisperBackend: transcribed in %.1fs " "(lang=%s, segments=%d, text_len=%d)",
                    duration,
                    info.language,
                    segment_count,
                    len(transcribed),
                )

                return TranscriptionResult(
                    success=True,
                    transcribed_text=transcribed,
                    confidence=avg_confidence,
                    language=info.language,
                    duration_seconds=info.duration,
                    audio_format=audio_format,
                    backend="faster_whisper",
                    source="faster_whisper",
                )

            finally:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

        except Exception as e:
            duration = time.monotonic() - start
            _logger.error(
                "FasterWhisperBackend: transcription failed in %.1fs: %s",
                duration,
                e,
            )
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="faster_whisper",
                error=f"Transcription error: {e}",
                source="faster_whisper",
            )

    def health_check(self) -> dict[str, Any]:
        return {
            "backend": "faster_whisper",
            "available": self.is_available,
            "model_size": self._model_size,
            "device": self._device,
            "compute_type": self._compute_type,
            "model_loaded": self._model is not None,
            "load_error": self._load_error,
        }


# ──────────────────────────────────────────────────────────────
#  WHISPER BACKEND — Whisper local (PyTorch)
# ──────────────────────────────────────────────────────────────


class WhisperBackend(STTBackend):
    """STT backend using Whisper local (PyTorch-based).

    The Whisper model running locally. Slower than faster-whisper but
    more widely available and tested.

    Requirements:
      pip install whisper

    Configuration:
      - model_size: tiny|base|small|medium|large
      - device: cpu|cuda
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        language: str = "",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._language = language
        self._model: Any | None = None
        self._load_error: str = ""

    @property
    def name(self) -> str:
        return "whisper"

    @property
    def is_available(self) -> bool:
        try:
            import whisper  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_model(self) -> Any:
        """Lazy-load the Whisper model (once)."""
        if self._model is not None:
            return self._model

        if self._load_error:
            return None

        try:
            import whisper

            _logger.info(
                "WhisperBackend: loading model=%s device=%s",
                self._model_size,
                self._device,
            )
            self._model = whisper.load_model(self._model_size, device=self._device)
            _logger.info("WhisperBackend: model loaded successfully")
            return self._model
        except Exception as e:
            self._load_error = str(e)
            _logger.error("WhisperBackend: model load failed: %s", e)
            return None

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Transcribe using Whisper local."""
        start = time.monotonic()

        if not audio_bytes:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="whisper",
                error="Empty audio bytes",
                source="whisper",
            )

        model = self._ensure_model()
        if model is None:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="whisper",
                error=f"Model not loaded: {self._load_error}",
                source="whisper",
            )

        try:
            import os
            import tempfile

            ext = audio_format if audio_format else "wav"
            suffix = f".{ext}" if not ext.startswith(".") else ext

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                lang = language or self._language or None
                options: dict[str, Any] = {}
                if lang:
                    options["language"] = lang

                result = model.transcribe(tmp_path, **options)
                transcribed = result.get("text", "").strip()

                # Extract segments for confidence
                segments = result.get("segments", [])
                avg_confidence = 0.0
                if segments:
                    total_prob = sum(s.get("avg_logprob", 0.0) for s in segments)
                    avg_confidence = min(1.0, max(0.0, (total_prob / len(segments) + 1.0) / 2.0))

                detected_lang = result.get("language", lang or "")

                duration = time.monotonic() - start
                _logger.info(
                    "WhisperBackend: transcribed in %.1fs (text_len=%d)",
                    duration,
                    len(transcribed),
                )

                return TranscriptionResult(
                    success=True,
                    transcribed_text=transcribed,
                    confidence=avg_confidence,
                    language=detected_lang,
                    audio_format=audio_format,
                    backend="whisper",
                    source="whisper",
                )

            finally:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

        except Exception as e:
            duration = time.monotonic() - start
            _logger.error(
                "WhisperBackend: transcription failed in %.1fs: %s",
                duration,
                e,
            )
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend="whisper",
                error=f"Transcription error: {e}",
                source="whisper",
            )

    def health_check(self) -> dict[str, Any]:
        return {
            "backend": "whisper",
            "available": self.is_available,
            "model_size": self._model_size,
            "device": self._device,
            "model_loaded": self._model is not None,
            "load_error": self._load_error,
        }


# ──────────────────────────────────────────────────────────────
#  BACKEND REGISTRY — Known backend classes
# ──────────────────────────────────────────────────────────────

_BACKEND_CLASSES: dict[str, type[STTBackend]] = {
    "dummy": DummyBackend,
    "faster_whisper": FasterWhisperBackend,
    "whisper": WhisperBackend,
}

# Default fallback chain — tried in order, first available wins
_DEFAULT_FALLBACK_CHAIN: Sequence[str] = (
    "faster_whisper",
    "whisper",
    "dummy",
)


# ──────────────────────────────────────────────────────────────
#  EAR — The STT Service
# ──────────────────────────────────────────────────────────────


class Ear:
    """Speech-to-Text service — the ONLY entry point for audio transcription.

    The Ear service manages STT backends using the Strategy Pattern:
      - Auto-detects the best available backend at startup
      - Supports explicit backend selection via config
      - Falls back through the chain if the primary backend fails
      - Thread-safe — safe for concurrent use
      - Tracks metrics for monitoring and health checks

    Design invariants:
      1. transcribe() NEVER raises — returns TranscriptionResult.
      2. INBOUND ONLY — audio → text. No TTS capability.
      3. At minimum, the dummy backend is always available.
      4. The active backend can be changed at runtime.

    Usage:
        # Auto-detect best backend
        ear = Ear()

        # Explicit backend configuration
        from ._types import STTBackendConfig
        config = STTBackendConfig(backend_name="faster_whisper", model_size="base")
        ear = Ear(config=config)

        # Transcribe
        result = ear.transcribe(audio_bytes, audio_format="ogg")
        if result.success:
            print(result.transcribed_text)
    """

    def __init__(
        self,
        config: STTBackendConfig | None = None,
        *,
        backends: Sequence[STTBackend] | None = None,
    ) -> None:
        """Initialize the Ear STT service.

        Args:
            config: Backend configuration. If None, auto-detects
                    the best available backend using the default
                    fallback chain.
            backends: Explicit list of backend instances. Overrides
                     auto-detection. First available wins.
        """
        self._config = config or STTBackendConfig()
        self._lock = threading.Lock()
        self._metrics = VoicePipelineMetrics()

        # Build backend instances
        if backends:
            # Explicit backends provided
            self._backends: list[STTBackend] = list(backends)
        else:
            # Build from config / auto-detect
            self._backends = self._build_backends(self._config)

        # Select active backend
        self._active: STTBackend = self._select_backend()

        _logger.info(
            "Ear: initialized with active_backend=%s " "(available_backends=%s)",
            self._active.name,
            [b.name for b in self._backends if b.is_available],
        )

    # ── Backend Management ────────────────────────────────────

    def _build_backends(self, config: STTBackendConfig) -> list[STTBackend]:
        """Build backend instances from configuration.

        If config.fallback_chain is set, builds those backends
        in order. Otherwise, uses the default fallback chain.
        """
        chain = config.fallback_chain or _DEFAULT_FALLBACK_CHAIN
        backends: list[STTBackend] = []

        for name in chain:
            cls = _BACKEND_CLASSES.get(name)
            if cls is None:
                _logger.warning("Ear: unknown backend '%s' — skipping", name)
                continue

            try:
                if name == "dummy":
                    backend = cls()
                elif name == "faster_whisper":
                    backend = cls(
                        model_size=config.model_size,
                        device=config.device,
                        compute_type=config.compute_type,
                        language=config.language,
                    )
                elif name == "whisper":
                    backend = cls(
                        model_size=config.model_size,
                        device=config.device,
                        language=config.language,
                    )
                else:
                    backend = cls()

                backends.append(backend)
            except Exception as e:
                _logger.warning("Ear: failed to create backend '%s': %s", name, e)

        # Always ensure at least the dummy backend
        if not backends or not any(b.name == "dummy" for b in backends):
            backends.append(DummyBackend())

        return backends

    def _select_backend(self) -> STTBackend:
        """Select the first available backend from the chain."""
        for backend in self._backends:
            if backend.is_available:
                return backend

        # Fallback to dummy (should always be available)
        return DummyBackend()

    def switch_backend(self, backend_name: str) -> bool:
        """Switch the active backend by name.

        Thread-safe. Returns True if the switch succeeded.
        """
        with self._lock:
            for backend in self._backends:
                if backend.name == backend_name and backend.is_available:
                    old_name = self._active.name
                    self._active = backend
                    _logger.info(
                        "Ear: switched backend %s → %s",
                        old_name,
                        backend_name,
                    )
                    return True

            _logger.warning(
                "Ear: cannot switch to '%s' — not available",
                backend_name,
            )
            return False

    @property
    def active_backend(self) -> str:
        """Name of the currently active backend."""
        return self._active.name

    @property
    def available_backends(self) -> list[str]:
        """Names of all available backends."""
        return [b.name for b in self._backends if b.is_available]

    # ── Core Transcription ────────────────────────────────────

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text.

        This is the main entry point for STT transcription.
        It tries the active backend, then falls back through
        the chain if it fails.

        NEVER raises — returns TranscriptionResult.

        Args:
            audio_bytes: Raw audio data in any supported format.
            audio_format: Hint about the audio format (e.g. "ogg", "mp3").
            language: Hint about the spoken language (e.g. "es", "en").

        Returns:
            TranscriptionResult with transcription text or error.
        """
        if not audio_bytes:
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                error="Empty audio bytes — nothing to transcribe",
                source="ear",
            )

        # Enforce max audio duration hint (soft limit)
        with self._lock:
            metrics = self._metrics
            metrics.total_transcriptions += 1

        start = time.monotonic()

        # Try active backend first
        result = self._try_transcribe(
            self._active,
            audio_bytes,
            audio_format,
            language,
        )

        # If active backend failed, try fallback chain
        if not result.success:
            for backend in self._backends:
                if backend.name == self._active.name:
                    continue  # Already tried
                if not backend.is_available:
                    continue

                _logger.info(
                    "Ear: falling back from '%s' to '%s'",
                    self._active.name,
                    backend.name,
                )
                result = self._try_transcribe(
                    backend,
                    audio_bytes,
                    audio_format,
                    language,
                )
                if result.success:
                    break

        # Update metrics
        duration = time.monotonic() - start
        with self._lock:
            if result.success:
                metrics.successful_transcriptions += 1
            else:
                metrics.failed_transcriptions += 1
            backend_name = result.backend or "unknown"
            metrics.backend_usage[backend_name] = metrics.backend_usage.get(backend_name, 0) + 1

        _logger.info(
            "Ear: transcription completed in %.2fs (success=%s, backend=%s, text_len=%d)",
            duration,
            result.success,
            result.backend,
            len(result.transcribed_text),
        )

        return result

    async def transcribe_async(
        self,
        audio_bytes: bytes,
        audio_format: str = "",
        language: str = "",
    ) -> TranscriptionResult:
        """Async wrapper for transcribe().

        Runs the synchronous transcription in a thread pool
        to avoid blocking the event loop.
        """
        return await asyncio.to_thread(
            self.transcribe,
            audio_bytes,
            audio_format,
            language,
        )

    def _try_transcribe(
        self,
        backend: STTBackend,
        audio_bytes: bytes,
        audio_format: str,
        language: str,
    ) -> TranscriptionResult:
        """Try transcription with a specific backend.

        Catches ALL exceptions — never raises.
        """
        try:
            result = backend.transcribe(audio_bytes, audio_format, language)
            # Ensure backend name is set
            if not result.backend:
                result.backend = backend.name
            return result
        except Exception as e:
            _logger.error(
                "Ear: backend '%s' raised unexpected error: %s",
                backend.name,
                e,
            )
            return TranscriptionResult(
                success=False,
                audio_format=audio_format,
                backend=backend.name,
                error=f"Unexpected error: {e}",
                source="ear_fallback",
            )

    # ── Monitoring ────────────────────────────────────────────

    @property
    def metrics(self) -> VoicePipelineMetrics:
        """Pipeline metrics snapshot."""
        with self._lock:
            # Return a copy to avoid external mutation
            return VoicePipelineMetrics(
                total_transcriptions=self._metrics.total_transcriptions,
                successful_transcriptions=self._metrics.successful_transcriptions,
                failed_transcriptions=self._metrics.failed_transcriptions,
                total_audio_seconds=self._metrics.total_audio_seconds,
                total_conversion_count=self._metrics.total_conversion_count,
                failed_conversions=self._metrics.failed_conversions,
                backend_usage=dict(self._metrics.backend_usage),
            )

    def health_check(self) -> dict[str, Any]:
        """Full health check of the Ear service and all backends."""
        return {
            "service": "ear",
            "active_backend": self._active.name,
            "available_backends": self.available_backends,
            "all_backends": [b.health_check() for b in self._backends],
            "metrics": {
                "total": self._metrics.total_transcriptions,
                "success_rate": self._metrics.success_rate,
            },
        }


# ──────────────────────────────────────────────────────────────
#  PUBLIC EXPORTS
# ──────────────────────────────────────────────────────────────

__all__ = [
    "_BACKEND_CLASSES",
    "_DEFAULT_FALLBACK_CHAIN",
    "DummyBackend",
    "Ear",
    "FasterWhisperBackend",
    "STTBackend",
    "WhisperBackend",
]
