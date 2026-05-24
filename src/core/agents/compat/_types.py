"""
Shared types, constants, and utilities for the compat layer.
"""

from __future__ import annotations

import logging

from src.core.shared.constants import VALID_INTENT_GOALS, VALID_INTENT_OPERATIONS

logger = logging.getLogger(__name__)

# Backward-compatible aliases
VALID_OPERATIONS = VALID_INTENT_OPERATIONS
VALID_GOALS = VALID_INTENT_GOALS
__all__ = ["VALID_GOALS", "VALID_OPERATIONS", "logger"]
