"""main_channels — Punto de entrada principal de Zenic-Agents.

Inicializa todo el sistema:
1. Carga configuración
2. Bootstrap de canales + sistema proactivo
3. Conecta los cables:
   - LocalDataScanner → SNA Monitors → AlertManager → ProactiveChannelBridge → Canal
   - Canal → A52/A53 → Engine → A53 deliver → Canal
4. Primer escaneo proactivo

El sistema VE los datos locales del usuario y puede
detectar problemas ANTES de que se manifiesten en canales.
"""

from __future__ import annotations

import sys
import os
import logging
import asyncio

# Añadir src al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.settings import ZenicConfig
from src.core.channel._bootstrap import ChannelBootstrap
from src.core.channel.a53_text import ChannelType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zenic.main")


async def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("  Zenic-Agents v3.0.0 — Sistema con Proactivo Local")
    logger.info("=" * 60)

    # 1. Cargar configuración
    config = ZenicConfig.from_env()
    logger.info(f"Configuración cargada:")
    logger.info(f"  BD: {config.database.path}")
    logger.info(f"  Canal proactivo: {config.channels.proactive_default_channel}")
    logger.info(f"  Destinatario: {config.channels.proactive_default_recipient or '(no configurado)'}")
    logger.info(f"  SNA: {'habilitado' if config.sna.enabled else 'deshabilitado'}")
    logger.info(f"  Autopilot: {'habilitado' if config.autopilot.enabled else 'deshabilitado'} ({config.autopilot.autonomy_level})")

    # 2. Mapear canal proactivo
    channel_map = {
        "whatsapp": ChannelType.WHATSAPP,
        "telegram": ChannelType.TELEGRAM,
        "web": ChannelType.WEB,
        "sms": ChannelType.SMS,
    }
    proactive_channel = channel_map.get(
        config.channels.proactive_default_channel,
        ChannelType.TELEGRAM,
    )

    # 3. Bootstrap
    bootstrap = ChannelBootstrap(
        db_path=config.database.path,
        base_path=config.data_base_path,
        config_path=config.sna.threshold_config_path,
        proactive_channel=proactive_channel,
        proactive_recipient=config.channels.proactive_default_recipient,
    )

    result = await bootstrap.bootstrap()

    if result["status"] == "ok":
        logger.info("=" * 60)
        logger.info("  ✓ Sistema inicializado correctamente")
        logger.info("  ✓ LocalDataScanner: ojos sobre datos locales")
        logger.info("  ✓ SNA: monitores escaneando BD local")
        logger.info("  ✓ ProactiveChannelBridge: alertas → canal del usuario")
        logger.info("=" * 60)

        # 4. Primer escaneo proactivo (demo)
        if config.sna.enabled and bootstrap.sna_engine:
            logger.info("Ejecutando primer escaneo proactivo...")
            alerts = bootstrap.sna_engine.full_scan()
            if alerts:
                logger.info(f"  {len(alerts)} alertas proactivas generadas y enviadas")
            else:
                logger.info("  Sistema saludable — sin alertas")

            # Health summary
            health = bootstrap.sna_engine.health_summary()
            logger.info(f"  Salud: {health['healthy']}/{health['total_monitors']} monitores OK")

        # 5. Stats del ProactiveChannelBridge
        if bootstrap.proactive_bridge:
            stats = bootstrap.proactive_bridge.get_stats()
            logger.info(f"  Bridge stats: {stats['sent_count']} enviados, {stats['failed_count']} fallidos")

    else:
        logger.error(f"Bootstrap falló: {result.get('error', 'unknown')}")
        return 1

    # 6. En modo interactivo, mantener vivo
    logger.info("\nSistema listo. Presiona Ctrl+C para detener.")

    try:
        # En producción, aquí iría el loop de eventos del bot
        # (webhook listener para WhatsApp/Telegram)
        while True:
            await asyncio.sleep(60)
            # Escaneo periódico del SNA
            if config.sna.enabled and bootstrap.sna_engine:
                alerts = bootstrap.sna_engine.check()
                if alerts:
                    logger.info(f"Escaneo SNA: {len(alerts)} alertas")
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
    finally:
        bootstrap.shutdown()
        logger.info("Zenic-Agents detenido correctamente")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
