#!/usr/bin/env python3
"""
Zenic-Agents — Modo Conversacional.

Dos modos de operacion:

  1. Modo CLI Interactivo (default):
     python3 main_conversational.py
     Asistente conversacional interactivo SIN servidor HTTP.

  2. Modo Servidor Webhook:
     python3 main_conversational.py --server
     Inicia servidor HTTP en puerto 9100 que recibe webhooks
     de WhatsApp/Telegram via Gateway (Next.js) y los procesa
     con el ConversationEngine. Las respuestas se envian de
     vuelta al usuario por el canal correspondiente.
"""

import argparse
import logging
import sys

from src.core.env_loader import load_env

load_env()

from src.core.shared._version import ZENIC_VERSION_STR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ZENIC.CONVERSATIONAL")


def _init_mini_ai():
    """Initialize MiniAIEngine (Qwen) for Layer 4 classification.

    Returns:
        MiniAIEngine instance or None if not available.
    """
    mini_ai = None
    try:
        from src.core.mini_ai_parts import MiniAIEngine

        mini_ai = MiniAIEngine()
        if mini_ai.is_loaded:
            logger.info(f"MiniAIEngine loaded ({mini_ai.stats['load_time_s']:.1f}s) — Layer 4 activo")
        else:
            logger.warning("MiniAIEngine: modelo no encontrado. Layer 4 desactivado.")
            mini_ai = None
    except Exception as e:
        logger.warning(f"MiniAIEngine unavailable: {e}. Layer 4 desactivado.")
        mini_ai = None
    return mini_ai


def _init_conversation_engine(mini_ai=None):
    """Initialize the ConversationEngine.

    Args:
        mini_ai: Optional MiniAIEngine instance for Layer 4.

    Returns:
        ConversationEngine instance.
    """
    from src.core.conversational import ConversationEngine

    engine = ConversationEngine(mini_ai_engine=mini_ai)
    if mini_ai is not None:
        logger.info("ConversationEngine + Layer 4 LLM initialized")
    else:
        logger.info("ConversationEngine initialized (sin Layer 4)")
    return engine


def _init_registry():
    """Initialize the AdapterRegistry with channel providers.

    Returns:
        AdapterRegistry with registered providers.
    """
    from src.core.channels import (
        AdapterRegistry,
        LogChannelProvider,
        TelegramChannelProvider,
        WhatsAppChannelProvider,
    )

    registry = AdapterRegistry()

    # Log provider (siempre disponible como fallback terminal)
    registry.register(LogChannelProvider())

    # WhatsApp (dry-run si no hay credenciales)
    try:
        wa = WhatsAppChannelProvider()
        registry.register(wa)
        logger.info(
            "WhatsApp provider: %s",
            "configurado" if wa.is_available else "dry-run (sin credenciales)",
        )
    except Exception as e:
        logger.warning(f"WhatsApp provider no disponible: {e}")

    # Telegram (dry-run si no hay credenciales)
    try:
        tg = TelegramChannelProvider()
        registry.register(tg)
        logger.info(
            "Telegram provider: %s",
            "configurado" if tg.is_available else "dry-run (sin credenciales)",
        )
    except Exception as e:
        logger.warning(f"Telegram provider no disponible: {e}")

    return registry


async def _run_server(host: str = "127.0.0.1", port: int = 9100) -> None:
    """Run the webhook server mode.

    Args:
        host: Host to bind the HTTP server.
        port: Port to bind the HTTP server.
    """
    import asyncio

    # 1. Initialize MiniAIEngine
    mini_ai = _init_mini_ai()

    # 2. Initialize ConversationEngine
    engine = _init_conversation_engine(mini_ai)

    # 3. Initialize registry with channel providers
    registry = _init_registry()

    # 4. Initialize ChannelGateway (bridge webhook → ConversationEngine)
    from src.core.channels import ChannelGateway, WebhookReceiver

    gateway = ChannelGateway(engine=engine, registry=registry)

    # 5. Initialize WebhookReceiver (HTTP server)
    receiver = WebhookReceiver(
        registry=registry,
        message_handler=gateway,
        host=host,
        port=port,
    )

    # 6. Start the server
    await receiver.start()

    print(f"\n{'=' * 60}")
    print(f"  ZENIC-AGENTS {ZENIC_VERSION_STR} — Servidor Webhook")
    print(f"  Motor: ConversationEngine + ChannelGateway")
    print(f"  Escuchando en: http://{host}:{port}/api/messages")
    print(f"  Canales: {', '.join(registry.registered_channels)}")
    print(f"  MiniAIEngine: {'ACTIVO' if mini_ai else 'DESACTIVADO'}")
    print(f"{'=' * 60}")
    print("  Presiona Ctrl+C para detener.")
    print(f"{'=' * 60}\n")

    # 7. Mantener vivo hasta Ctrl+C
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        await receiver.stop()
        gateway_stats = gateway.stats
        logger.info(
            "Servidor detenido. Mensajes: %d recibidos, %d procesados, %d enviados",
            gateway_stats["total_received"],
            gateway_stats["total_processed"],
            gateway_stats["total_sent"],
        )


def _run_cli_interactive(mini_ai=None) -> None:
    """Run the interactive CLI mode.

    Args:
        mini_ai: Optional MiniAIEngine instance.
    """
    import asyncio

    engine = _init_conversation_engine(mini_ai)

    print(f"\n{'=' * 60}")
    print(f"  ZENIC-AGENTS {ZENIC_VERSION_STR} — Asistente Conversacional")
    print(f"  Motor: {type(engine).__name__}")
    print("  Modo: Local (sin servidor HTTP)")
    print(f"{'=' * 60}")
    print("  Escribe tu consulta. 'quit' para salir.")
    print(f"{'=' * 60}\n")

    while True:
        try:
            user_input = input("zenic-chat> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        try:
            loop = asyncio.new_event_loop()
            resp = loop.run_until_complete(
                engine.process_message(session_id="cli", user_message=user_input)
            )
            loop.close()

            if resp:
                print(f"  {resp.content}")
            else:
                print("  (sin respuesta)")
        except Exception as e:
            print(f"  Error: {e}")

    print("\n  Hasta luego!")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"ZENIC-AGENTS {ZENIC_VERSION_STR} - Asistente Conversacional"
    )
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument(
        "--server",
        action="store_true",
        help="Modo servidor webhook (recibe mensajes de WhatsApp/Telegram via Gateway)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host del servidor webhook (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9100,
        help="Puerto del servidor webhook (default: 9100)",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize MiniAIEngine (Qwen) for Layer 4
    mini_ai = _init_mini_ai()

    if args.server:
        # Modo servidor
        import asyncio

        asyncio.run(_run_server(host=args.host, port=args.port))
    else:
        # Modo CLI interactivo
        _run_cli_interactive(mini_ai)


if __name__ == "__main__":
    main()
