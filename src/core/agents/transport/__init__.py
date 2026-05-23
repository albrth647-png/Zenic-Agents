"""
ZENIC-AGENTS v18 — Layer 10: Transport Agents

Channel transport agents handle the movement of text and voice
between the core system and external channels.

Design invariants:
  1. Transport agents are deterministic — no AI calls.
  2. They are NOT chatbots — they transport, format, and deliver.
  3. Core NEVER knows if input came as text or voice.
  4. Core ALWAYS responds in text (per user constraint).

Agents:
  A53 — TextChannelAgent: text sanitize/format/truncate/split/route/deliver/fallback
  A52 — VoiceChannelAgent: audio download/decode/STT/transcribe → text
"""

from .text_channel_agent import TextChannelAgent
from .voice_channel_agent import VoiceChannelAgent

__all__ = [
    "TextChannelAgent",
    "VoiceChannelAgent",
]
