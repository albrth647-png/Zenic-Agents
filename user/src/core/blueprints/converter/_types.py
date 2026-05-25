"""Types and constants for converter."""

from __future__ import annotations

import logging

from ..types import BlueprintTier

logger = logging.getLogger(__name__)

_SENSITIVITY_TIER_MAP: dict[str, BlueprintTier] = {
    "low": BlueprintTier.FREE,
    "medium": BlueprintTier.FREE,
    "high": BlueprintTier.PRO,
    "critical": BlueprintTier.ENTERPRISE,
}
__all__ = ["_SENSITIVITY_TIER_MAP", "logger"]
