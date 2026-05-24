"""Types and constants for sna_engine."""

from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_default_engine: Optional[Any] = None
__all__ = ["_default_engine", "logger"]
