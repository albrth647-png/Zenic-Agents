"""ChannelBootstrap — Conecta todos los cables del sistema.

12+ pasos para inicializar:
1-4:   Canales básicos (WhatsApp, Telegram, Web, SMS)
5-6:   A52 (voz) y A53 (texto)
7-8:   MessageBridge (reactivo)
9-10:  SNA + LocalDataScanner
11-12: ProactiveChannelBridge + AutopilotChannelInterceptor (proactivo)

Después del bootstrap, el sistema VE los datos locales del usuario
y puede notificar proactivamente por su canal preferido.
"""

from __future__ import annotations

import logging
from typing import Any

from src.data.local_scanner import LocalDataScanner
from src.core.channel.a52_voice import VoiceChannelAgent
from src.core.channel.a53_text import TextChannelAgent, ChannelType
from src.core.channel.message_bridge import MessageBridge
from src.core.channel._proactive import (
    ProactiveChannelBridge,
    AutopilotChannelInterceptor,
    create_sna_callback,
)
from src.core.sna.sna_engine import SNAEngine
from src.core.sna.alert_manager import AlertManager
from src.core.sna.thresholds import ThresholdEngine
from src.core.safety.safety_gate import SafetyGate

logger = logging.getLogger(__name__)


class ChannelBootstrap:
    """Bootstrap del sistema completo de canales + sistema proactivo.

    Inicializa todos los componentes y los conecta entre sí.
    Al final, el sistema:
    - Recibe mensajes reactivos de canales
    - Escanea datos locales proactivamente
    - Envía alertas al usuario por su canal preferido
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
        self.proactive_bridge: ProactiveChannelBridge | None = None
        self.autopilot_interceptor: AutopilotChannelInterceptor | None = None
        self.safety_gate: SafetyGate | None = None

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

            # Step 3: VoiceChannelAgent (A52)
            self._step(3, "VoiceChannelAgent (A52)")
            self.voice_agent = VoiceChannelAgent()
            steps["3_voice_agent"] = "ok"

            # Step 4: TextChannelAgent (A53)
            self._step(4, "TextChannelAgent (A53)")
            self.text_agent = TextChannelAgent()
            steps["4_text_agent"] = "ok"

            # Step 5: MessageBridge (reactivo)
            self._step(5, "MessageBridge")
            self.message_bridge = MessageBridge(
                voice_agent=self.voice_agent,
                text_agent=self.text_agent,
            )
            steps["5_message_bridge"] = "ok"

            # Step 6: Registrar canales
            self._step(6, "Registrar canales")
            self.message_bridge.register_channel("whatsapp", ChannelType.WHATSAPP)
            self.message_bridge.register_channel("telegram", ChannelType.TELEGRAM)
            self.message_bridge.register_channel("web", ChannelType.WEB)
            steps["6_channels_registered"] = "ok"

            # Step 7: ProactiveChannelBridge
            self._step(7, "ProactiveChannelBridge")
            self.proactive_bridge = ProactiveChannelBridge(
                text_agent=self.text_agent,
                default_channel=self.proactive_channel,
                default_recipient=self.proactive_recipient,
            )
            steps["7_proactive_bridge"] = "ok"

            # Step 8: AutopilotChannelInterceptor
            self._step(8, "AutopilotChannelInterceptor")
            self.autopilot_interceptor = AutopilotChannelInterceptor(
                bridge=self.proactive_bridge
            )
            steps["8_autopilot_interceptor"] = "ok"

            # Step 9: SNA Engine (con callback → bridge)
            self._step(9, "SNAEngine + LocalDataScanner")
            sna_callback = create_sna_callback(self.proactive_bridge)
            self.sna_engine = SNAEngine(
                db_path=self.db_path,
                base_path=self.base_path,
                config_path=self.config_path,
                on_alert=sna_callback,
            )
            steps["9_sna_engine"] = "ok"

            # Step 10: Verificar acceso a datos locales
            self._step(10, "Verificar acceso a datos locales")
            scan = self.scanner.scan_database_schema()
            steps["10_db_access"] = "ok" if scan.get("status") in ("ok", "empty") else f"warning: {scan.get('status')}"

            # Step 11: Primer escaneo proactivo
            self._step(11, "Primer escaneo proactivo")
            health = self.sna_engine.health_summary()
            steps["11_first_scan"] = f"healthy={health['healthy']}, issues={health['unhealthy']}"

            # Step 12: Conexiones completadas
            self._step(12, "Conexiones completadas")
            self._initialized = True
            steps["12_complete"] = "ok"

            logger.info("=== ChannelBootstrap completado exitosamente ===")
            return {"status": "ok", "steps": steps, "health": health}

        except Exception as e:
            logger.error(f"Bootstrap falló en paso: {e}")
            return {"status": "error", "steps": steps, "error": str(e)}

    def _step(self, number: int, name: str):
        """Log de paso de bootstrap."""
        logger.info(f"  [{number:02d}/12] {name}...")

    def is_initialized(self) -> bool:
        return self._initialized

    def shutdown(self):
        """Cierra todos los componentes."""
        if self.sna_engine:
            self.sna_engine.close()
        if self.scanner:
            self.scanner.close()
        logger.info("ChannelBootstrap shutdown completo")
