"""Transport layer data types for v18 single-responsibility agents.

Layer 10: Transport — Channel text/voice delivery agents (A52, A53).

Design invariants:
  1. No channel-specific types leak into transport types.
  2. All string fields default to empty — never raise on missing data.
  3. Priority and status are plain strings — conversion happens in the agent.
  4. Every result carries a `source` field for audit tracing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

# ────────────────────────────── A53: Text Channel ──────────────────────────────

@dataclass
class TextChannelInput:
    """Input for A53 TextChannelAgent.

    Contains everything needed to deliver a text message
    through the channel system: the raw text, target channel,
    recipient, and delivery preferences.

    The agent handles sanitization, formatting, truncation,
    splitting, routing, and fallback — the caller just provides
    the text and where it should go.
    """

    text: str = ""                              # Raw text to deliver
    channel: str = ""                           # Target channel name (e.g. "whatsapp", "telegram")
    recipient: str = ""                         # Recipient identifier (chat_id, phone, email)
    priority: str = "normal"                    # Priority: low|normal|high|urgent|emergency
    reply_to: str = ""                          # Message ID to reply to (if supported)
    thread_id: str = ""                         # Thread/conversation ID (if supported)
    metadata: dict[str, Any] = field(default_factory=dict)
    max_chunks: int = 10                        # Safety limit: max message splits allowed
    fallback_channels: Sequence[str] = ()       # Override default fallback chain


@dataclass
class TextChannelResult:
    """Output of A53 TextChannelAgent.

    Captures the full delivery outcome including which channel
    actually delivered (may differ from the requested channel
    due to fallback), how many messages were sent (after splitting),
    and any truncation or fallback indicators.
    """

    success: bool = False                       # All chunks delivered successfully
    channel_used: str = ""                      # Actual channel that delivered the last chunk
    original_channel: str = ""                  # Originally requested channel
    messages_sent: int = 0                      # Number of chunks successfully sent
    message_ids: list[str] = field(default_factory=list)  # Platform message IDs
    status: str = "pending"                     # pending|sent|delivered|failed|fallback|dry_run
    truncated: bool = False                     # Was any chunk truncated?
    split_count: int = 0                        # Total number of chunks (1 = no split)
    fallback_used: bool = False                 # Was a fallback channel used?
    original_length: int = 0                    # Length of original raw text
    delivered_length: int = 0                   # Total length of delivered text
    error: str = ""                             # Error details if failed
    source: str = "deterministic"               # Audit source trace


# ────────────────────────────── A52: Voice Channel ──────────────────────────────

@dataclass
class VoiceChannelInput:
    """Input for A52 VoiceChannelAgent.

    Contains an audio reference (URL, path, or raw bytes metadata)
    for inbound transcription, or text for outbound TTS synthesis.

    IMPORTANT PER USER CONSTRAINT:
      The motor reads audios but responds ONLY in text.
      Outbound TTS is NOT used — this input type exists for
      inbound audio→text transcription only.
    """

    audio_url: str = ""                         # Download URL for the audio
    audio_path: str = ""                        # Local filesystem path (alternative)
    audio_format: str = ""                      # Detected/provided format: ogg|mp3|wav|m4a|opus
    channel: str = ""                           # Source channel name
    sender: str = ""                            # Sender identifier
    duration_seconds: float = 0.0               # Audio duration (if known)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceChannelResult:
    """Output of A52 VoiceChannelAgent.

    Contains the transcription text from inbound audio.
    The core system NEVER knows if input came as text or voice —
    it always receives text.

    Outbound TTS is NOT produced per user constraint:
      "quiero solo que mi motor responda y lea audios pero
       responda en texto Nono en audio"
    """

    success: bool = False
    transcribed_text: str = ""                  # STT transcription result
    channel: str = ""                           # Source channel
    audio_format: str = ""                      # Original audio format
    duration_seconds: float = 0.0               # Original audio duration
    confidence: float = 0.0                     # STT confidence (0.0-1.0)
    language: str = ""                          # Detected language
    error: str = ""
    source: str = "deterministic"
