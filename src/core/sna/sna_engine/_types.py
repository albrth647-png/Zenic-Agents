"""Types and constants for sna_engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_default_engine: Any | None = None
__all__ = ["_default_engine", "logger"]
