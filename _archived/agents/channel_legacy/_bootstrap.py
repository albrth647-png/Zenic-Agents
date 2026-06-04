"""ChannelBootstrap — Conecta todos los cables del sistema.

12+ pasos para inicializar:
1-4:   Canales básicos (WhatsApp, Telegram, Web, SMS)
5-6:   A52 (voz) y A53 (texto)
7-8:   MessageBridge (reactivo)
9-10:  SNA + LocalDataScanner
11-12: ProactiveChannelBridge + AutopilotChannelInterceptor (proactivo)


ESTRATEGIA DE MIGRACIÓN (Fase 3):
  Ahora registra providers REALES (Telegram, WhatsApp, TwilioSMS, etc.)
  en el AdapterRegistry del nuevo sistema core/channels/.
  El ProactiveChannelBridge usa el CompatibilityBridge para enviar
  a través del nuevo sistema con fallback automático.

  Si los providers reales no están disponibles (sin API keys),
  el sistema cae en dry-run mode automáticamente.
"""

from __future__ import annotations

import logging
from typing import Any

from ._compat_bridge import CompatibilityBridge
from ._proactive import (
    AutopilotChannelInterceptor,
    ProactiveChannelBridge,
    create_sna_callback,
)
from .a52_voice import VoiceChannelAgent
from .a53_text import ChannelType, TextChannelAgent
from .message_bridge import MessageBridge

# ── External imports (wrapped: may not be available in standalone mode) ───
try:
    from src.core.channels._registry import (
        AdapterRegistry,
        get_default_registry,
    )
    from src.core.channels._registry._discovery import ChannelRouter
    from src.core.safety.safety_gate import SafetyGate
    from src.core.sna.alert_manager import AlertManager
    from src.core.sna.sna_engine import SNAEngine
    from src.data.local_scanner import LocalDataScanner
    from src.core.channels.providers.telegram import TelegramChannelProvider
    from src.core.channels.providers.whatsapp import WhatsAppChannelProvider
    from src.core.channels.providers.twilio_sms import TwilioSMSChannelProvider
    from src.core.channels.providers.email import EmailChannelProvider
    from src.core.channels._sna_bridge import SNAChannelBridge
    from src.core.channels._webhook_receiver import get_webhook_receiver as _get_webhook_receiver
    _EXTERNAL_AVAILABLE = True
except ImportError:
    AdapterRegistry = None  # type: ignore[assignment,misc]
    get_default_registry = None  # type: ignore[assignment]
    ChannelRouter = None  # type: ignore[assignment,misc]
    SafetyGate = None  # type: ignore[assignment,misc]
    AlertManager = None  # type: ignore[assignment,misc]
    SNAEngine = None  # type: ignore[assignment,misc]
    LocalDataScanner = None  # type: ignore[assignment,misc]
    TelegramChannelProvider = None  # type: ignore[assignment,misc]
    WhatsAppChannelProvider = None  # type: ignore[assignment,misc]
    TwilioSMSChannelProvider = None  # type: ignore[assignment,misc]
    EmailChannelProvider = None  # type: ignore[assignment,misc]
    SNAChannelBridge = None  # type: ignore[assignment,misc]
    _get_webhook_receiver = None  # type: ignore[assignment]
    _EXTERNAL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChannelBootstrap:
    """Bootstrap del sistema completo de canales + sistema proactivo.

    Inicializa todos los componentes y los conecta entre sí.
    Ahora registra providers REALES en el AdapterRegistry.

    Al final, el sistema:
    - Recibe mensajes reactivos de canales (via nuevo sistema)
    - Escanea datos locales proactivamente
    - Envía alertas al usuario por su canal preferido (via nuevo sistema)
    """

    def __init__(
        self,
        db_path: str | None = None,
        base_path: str | None = None,
        config_path: str | None = None,
        proactive_channel: ChannelType = ChannelType.TELEGRAM,
        proactive_recipient: str = "",
    ):
        self.db_path = db_path
        self.base_path = base_path
        self.config_path = config_path
        self.proactive_channel = proactive_channel
        self.proactive_recipient = proactive_recipient

        # Componentes (se inicializan en bootstrap)
        self.scanner: LocalDataScanner | None = None
        self.voice_agent: VoiceChannelAgent | None = None
        self.text_agent: TextChannelAgent | None = None
        self.message_bridge: MessageBridge | None = None
        self.sna_engine: SNAEngine | None = None
        self.alert_manager: AlertManager | None = None
        self.proactive_bridge: ProactiveChannelBridge | None = None
        self.sna_bridge: SNAChannelBridge | None = None
        self.autopilot_interceptor: AutopilotChannelInterceptor | None = None
        self.safety_gate: SafetyGate | None = None
        self.compat_bridge: CompatibilityBridge | None = None
        self.registry: AdapterRegistry | None = None
        self.router: ChannelRouter | None = None
        self.webhook_receiver: Any | None = None

        self._initialized = False

    async def bootstrap(self) -> dict[str, Any]:
        """Ejecuta todos los pasos de inicialización."""
        logger.info("=== Iniciando ChannelBootstrap ===")
        steps = {}

        try:
            # Step 1: LocalDataScanner (ojos sobre datos locales)
            self._step(1, "LocalDataScanner")
            self.scanner = LocalDataScanner(db_path=self.db_path, base_path=self.base_path)
            steps["1_local_scanner"] = "ok"

            # Step 2: SafetyGate (inbypassable)
            self._step(2, "SafetyGate")
            self.safety_gate = SafetyGate()
            steps["2_safety_gate"] = "ok"

            # Step 3: AdapterRegistry + providers reales
            self._step(3, "AdapterRegistry + providers reales")
            self.registry = get_default_registry()

            # Instanciar providers reales
            telegram = TelegramChannelProvider()
            whatsapp = WhatsAppChannelProvider()
            twilio = TwilioSMSChannelProvider()
            email = EmailChannelProvider()

            # Registrar en el registry
            self.registry.register(telegram)
            self.registry.register(whatsapp)
            self.registry.register(twilio)
            self.registry.register(email)

            # Configurar cadenas de fallback
            self.registry.set_fallback_chain("telegram", ["whatsapp", "sms", "email", "log"])
            self.registry.set_fallback_chain("whatsapp", ["telegram", "sms", "email", "log"])
            self.registry.set_fallback_chain("sms", ["telegram", "email", "log"])
            self.registry.set_fallback_chain("email", ["telegram", "log"])

            # Crear router
            self.router = ChannelRouter(self.registry)

            # Start providers (async)
            await telegram.start()
            await whatsapp.start()
            await twilio.start()
            await email.start()

            steps["3_registry_providers"] = (
                f"telegram={telegram.is_available}, "
                f"whatsapp={whatsapp.is_available}, "
                f"sms={twilio.is_available}, "
                f"email={email.is_available}"
            )

            # Step 4: CompatibilityBridge (puente legacy → nuevo sistema)
            self._step(4, "CompatibilityBridge")
            self.compat_bridge = CompatibilityBridge(registry=self.registry)
            steps["4_compat_bridge"] = "ok"

            # Step 5: AlertManager
            self._step(5, "AlertManager")
            self.alert_manager = AlertManager()
            steps["5_alert_manager"] = "ok"

            # Step 6: VoiceChannelAgent (A52)
            self._step(6, "VoiceChannelAgent (A52)")
            self.voice_agent = VoiceChannelAgent()
            steps["6_voice_agent"] = "ok"

            # Step 7: TextChannelAgent (A53) — legacy
            self._step(7, "TextChannelAgent (A53)")
            self.text_agent = TextChannelAgent()
            steps["7_text_agent"] = "ok"

            # Step 8: MessageBridge (reactivo legacy)
            self._step(8, "MessageBridge")
            self.message_bridge = MessageBridge(
                voice_agent=self.voice_agent,
                text_agent=self.text_agent,
            )
            # Legacy channel registration
            self.message_bridge.register_channel("whatsapp", ChannelType.WHATSAPP)
            self.message_bridge.register_channel("telegram", ChannelType.TELEGRAM)
            self.message_bridge.register_channel("web", ChannelType.WEB)
            steps["8_message_bridge"] = "ok"

            # Step 8.5: WebhookReceiver (gateway → core bridge)
            self._step(8.5, "WebhookReceiver")
            self.webhook_receiver = _get_webhook_receiver(registry=self.registry)
            await self.webhook_receiver.start()
            steps["8.5_webhook_receiver"] = (
                f"running={self.webhook_receiver.is_running}, "
                f"host={self.webhook_receiver.host}:{self.webhook_receiver.port}"
            )

            # Step 9: SNAChannelBridge (nuevo bridge proactivo)
            self._step(9, "SNAChannelBridge")
            self.sna_bridge = SNAChannelBridge(
                alert_manager=self.alert_manager,
                registry=self.registry,
                router=self.router,
                default_recipient=self.proactive_recipient,
            )
            steps["9_sna_bridge"] = "ok"

            # Step 10: ProactiveChannelBridge (legacy) + CompatibilityBridge
            self._step(10, "ProactiveChannelBridge")
            self.proactive_bridge = ProactiveChannelBridge(
                text_agent=self.text_agent,
                default_channel=self.proactive_channel,
                default_recipient=self.proactive_recipient,
                compat_bridge=self.compat_bridge,
            )
            steps["10_proactive_bridge"] = "ok"

            # Step 11: AutopilotChannelInterceptor + SNA Engine
            self._step(11, "Autopilot + SNA Engine")
            self.autopilot_interceptor = AutopilotChannelInterceptor(bridge=self.proactive_bridge)

            # Crear callback SNA → ProactiveChannelBridge (legacy)
            sna_callback = create_sna_callback(self.proactive_bridge)

            self.sna_engine = SNAEngine(
                db_path=self.db_path,
                base_path=self.base_path,
                config_path=self.config_path,
                on_alert=sna_callback,
            )
            steps["11_sna_engine"] = "ok"

            # Step 12: Verificación final
            self._step(12, "Verificación final")
            scan = self.scanner.scan_database_schema()
            steps["12_verification"] = (
                f"db={scan.get('status', 'unknown')}, "
                f"providers={len(self.registry.registered_channels)}"
            )

            self._initialized = True
            logger.info("=== ChannelBootstrap completado exitosamente ===")

            return {
                "status": "ok",
                "steps": steps,
                "registered_providers": self.registry.registered_channels,
            }

        except Exception as e:
            logger.error(f"Bootstrap falló en paso: {e}")
            return {"status": "error", "steps": steps, "error": str(e)}

    def _step(self, number: int, name: str):
        """Log de paso de bootstrap."""
        logger.info(f"  [{number:02d}/12] {name}...")

    def is_initialized(self) -> bool:
        return self._initialized

    async def shutdown(self):
        """Cierra todos los componentes."""
        if self.sna_engine:
            self.sna_engine.close()
        if self.scanner:
            self.scanner.close()
        if self.registry:
            await self.registry.stop_all()
        if self.webhook_receiver:
            await self.webhook_receiver.stop()
        if self.message_bridge:
            self.message_bridge = None
        logger.info("ChannelBootstrap shutdown completo")
