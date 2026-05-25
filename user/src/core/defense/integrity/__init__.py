"""Re-exports for integrity package."""

import threading
from typing import Any

from ._mixin_core import IntegrityVerifier
from ._types import _SAFE_IDENTIFIER_RE, IntegrityCheckResult, IntegrityStatus

_lock = threading.Lock()

__all__ = [
    "_SAFE_IDENTIFIER_RE",
    "IntegrityCheckResult",
    "IntegrityStatus",
    "IntegrityVerifier",
    "get_integrity_verifier",
    "reset_integrity_verifier",
]


def get_integrity_verifier(**kwargs: Any) -> IntegrityVerifier:
    """Get or create the global IntegrityVerifier instance."""
    global _integrity_verifier
    with _lock:
        if _integrity_verifier is None:
            _integrity_verifier = IntegrityVerifier(**kwargs)
        return _integrity_verifier


def reset_integrity_verifier() -> None:
    """Reset the global IntegrityVerifier (for testing)."""
    global _integrity_verifier
    if _integrity_verifier and _integrity_verifier._running:
        _integrity_verifier.stop_monitoring()
    _integrity_verifier = None
