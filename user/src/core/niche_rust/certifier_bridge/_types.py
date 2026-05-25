"""
Certifier Bridge — Types and FFI imports.

Contains CertificationResultPy dataclass and the Rust extension
import block shared by certifier sub-modules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Rust Extension Import
# ──────────────────────────────────────────────────────────────

NATIVE_AVAILABLE: bool = False
_native = None

try:
    import _zenic_native as _native  # type: ignore[import-not-found]

    NATIVE_AVAILABLE = True
except ImportError:
    logger.warning(
        "CertifierBridge: _zenic_native extension not available. "
        "Run 'maturin develop' to build the Rust extension. "
        "Falling back to no-op mode."
    )


# ──────────────────────────────────────────────────────────────
#  CertificationResult — Python-side result wrapper
# ──────────────────────────────────────────────────────────────


@dataclass
class CertificationResultPy:
    """Python-side result of a certification operation.

    Wraps the Rust CertificationResult with additional Python-level
    metadata and convenience methods.

    Attributes:
        success: Whether the certification was successful.
        blueprint_id: The unique blueprint identifier (if certified).
        content_hash: The canonical BLAKE3 hash of the blueprint.
        status: Certification status string (draft, signed, verified, error).
        blueprint_dict: Phase 5 compatible dict (if certified).
        yaml_string: YAML export string (if certified).
        warnings: List of warning messages.
        errors: List of error messages.
    """

    success: bool = False
    blueprint_id: str | None = None
    content_hash: str = ""
    status: str = "error"
    blueprint_dict: dict[str, Any] | None = None
    yaml_string: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_certified(self) -> bool:
        """Check if the blueprint was successfully certified."""
        return self.success and self.status in ("signed", "verified")

    def summary(self) -> dict[str, Any]:
        """Get a summary dict for display purposes."""
        return {
            "success": self.success,
            "blueprint_id": self.blueprint_id,
            "content_hash": self.content_hash[:16] + "..." if len(self.content_hash) > 16 else self.content_hash,
            "status": self.status,
            "is_certified": self.is_certified,
            "warnings": len(self.warnings),
            "errors": len(self.errors),
        }


__all__ = ["NATIVE_AVAILABLE", "CertificationResultPy", "_native", "logger"]
