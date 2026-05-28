"""twilio_sms — Type definitions."""

from __future__ import annotations

import ipaddress
import logging
import urllib.parse
from urllib.parse import urlparse

logger = logging.getLogger("zenic_agents.channels.twilio_sms")


def _validate_url(url: str, allowed_schemes: tuple = ("http", "https")) -> str:
    """Validate URL to prevent SSRF attacks."""
    parsed = urlparse(url)
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed. Use: {allowed_schemes}")
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass  # hostname is not an IP, that's OK
    else:
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            raise ValueError(f"Access to internal IPs is not allowed: {parsed.hostname}")
    return url


# ── Optional Dependencies ─────────────────────────────────────

try:
    import aiohttp  # noqa: F401

    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

try:
    import urllib.error
    import urllib.request  # noqa: F401

    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False


# ── Constants ─────────────────────────────────────────────────

_TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5
_HTTP_TIMEOUT = 30
_SMS_CHAR_LIMIT = 160
_MMS_CHAR_LIMIT = 1600
__all__ = [
    "_HTTP_TIMEOUT",
    "_MAX_RETRIES",
    "_MMS_CHAR_LIMIT",
    "_RETRY_BASE_DELAY",
    "_SMS_CHAR_LIMIT",
    "_TWILIO_API_BASE",
    "_validate_url",
    "logger",
]
