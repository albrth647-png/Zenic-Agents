"""Channel System — Canales de comunicación con el usuario.

A52 (VoiceChannelAgent): download→validate→convert→transcribe→deliver text
A53 (TextChannelAgent): sanitize→limit→truncate/split→route→deliver→fallback
MessageBridge: Canal→A52/A53→Engine→A53 deliver→Canal response
ProactiveChannelBridge: SNA/Autopilot→A53 deliver→Canal (mensajes proactivos)
"""

from src.core.channel._bootstrap import ChannelBootstrap
from src.core.channel._proactive import ProactiveChannelBridge
from src.core.channel.a52_voice import VoiceChannelAgent
from src.core.channel.a53_text import TextChannelAgent
from src.core.channel.message_bridge import MessageBridge

__all__ = [
    "ChannelBootstrap",
    "MessageBridge",
    "ProactiveChannelBridge",
    "TextChannelAgent",
    "VoiceChannelAgent",
]
