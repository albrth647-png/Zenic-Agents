"""email — Type definitions."""

from __future__ import annotations

import logging
from typing import Dict


logger = logging.getLogger("zenic_agents.channels.email")

# ── Optional Dependencies ─────────────────────────────────────────

try:
    import aiohttp  # noqa: F401
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

# ── Constants ──────────────────────────────────────────────────────

_VALID_MODES = frozenset({"smtp", "graph_api", "auto"})

# Priority → importance mapping (ChannelPriority → email importance)
_PRIORITY_TO_IMPORTANCE: Dict[str, str] = {
    "low": "low",
    "normal": "normal",
    "high": "high",
    "urgent": "high",
    "emergency": "high",
}
__all__ = ["_PRIORITY_TO_IMPORTANCE", "_VALID_MODES", "logger"]
