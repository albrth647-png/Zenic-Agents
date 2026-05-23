"""ZENIC-AGENTS - Channel Formatter: Platform Limits"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


class PlatformLimits:
    """Character/content limits per platform.

    Text limits control truncation/splitting in the formatter.
    Voice limits control audio size/duration validation in the
    voice pipeline.
    """
    # ── Text limits ──
    telegram_text: int = 4096
    telegram_caption: int = 1024
    discord_text: int = 2000
    discord_embed_title: int = 256
    discord_embed_description: int = 2048
    discord_embed_fields: int = 25
    discord_embed_field_name: int = 256
    discord_embed_field_value: int = 1024
    discord_embed_footer: int = 2048
    slack_text: int = 3000
    slack_block_text: int = 3000
    teams_text: int = 18000           # Adaptive Card body limit
    whatsapp_text: int = 4096
    sms_text: int = 160
    sms_mms_text: int = 1600

    # ── Voice/Audio limits ──
    # Maximum audio duration in seconds per platform
    whatsapp_voice_max_duration: int = 600     # 10 minutes
    telegram_voice_max_duration: int = 1800    # 30 minutes (Telegram Bot API)
    discord_voice_max_duration: int = 600      # 10 minutes

    # Maximum audio file size in bytes per platform
    whatsapp_voice_max_size: int = 16 * 1024 * 1024    # 16 MB
    telegram_voice_max_size: int = 20 * 1024 * 1024    # 20 MB
    discord_voice_max_size: int = 25 * 1024 * 1024     # 25 MB

    # Maximum transcription text length per platform
    # (after STT, the transcription is passed as text through A53)
    transcription_max_length: int = 4096


# Default singleton instance
LIMITS = PlatformLimits()