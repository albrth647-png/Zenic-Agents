"""email_executor — Type definitions."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Optional: aiosmtplib ──────────────────────────────────────────

try:
    import aiosmtplib  # type: ignore[import-unresolved]  # noqa: F401

    _HAS_AIOSMTPLIB_LOCAL = True
except ImportError:
    _HAS_AIOSMTPLIB_LOCAL = False

# ── Optional: urllib fallback ─────────────────────────────────────

try:
    import urllib.error
    import urllib.request  # noqa: F401

    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False

# ── Constants ──────────────────────────────────────────────────────

_VALID_MODES = frozenset({"smtp", "graph_api", "auto"})
_VALID_IMPORTANCE = frozenset({"low", "normal", "high"})
_SMTP_TIMEOUT = 30  # seconds
__all__ = ["_SMTP_TIMEOUT", "_VALID_IMPORTANCE", "_VALID_MODES", "logger"]
