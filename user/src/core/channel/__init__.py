"""Channel System — Canales de comunicación con el usuario.

A52 (VoiceChannelAgent): download→validate→convert→transcribe→deliver text
A53 (TextChannelAgent): sanitize→limit→truncate/split→route→deliver→fallback
MessageBridge: Canal→A52/A53→Engine→A53 deliver→Canal response
ProactiveChannelBridge: SNA/Autopilot→A53 deliver→Canal (mensajes proactivos)

⚠️ DEPRECATED (Fase 3): Este módulo legacy será reemplazado por
   core/channels/ (nuevo sistema unificado de canales).
   - TextChannelAgent → AdapterRegistry.send_with_fallback()
   - ProactiveChannelBridge con CompatibilityBridge (usa providers reales)
   - Nuevo: SNAChannelBridge (core/channels/_sna_bridge.py)
   - Nuevo: ChannelRouter (core/channels/_registry/_router.py)
"""

import warnings

warnings.warn(
    "core/channel/ is deprecated. Use core/channels/ instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.core.channel._bootstrap import ChannelBootstrap
from src.core.channel._compat_bridge import CompatibilityBridge
from src.core.channel._proactive import ProactiveChannelBridge
from src.core.channel.a52_voice import VoiceChannelAgent
from src.core.channel.a53_text import TextChannelAgent
from src.core.channel.message_bridge import MessageBridge

__all__ = [
    "ChannelBootstrap",
    "CompatibilityBridge",
    "MessageBridge",
    "ProactiveChannelBridge",
    "TextChannelAgent",
    "VoiceChannelAgent",
]
