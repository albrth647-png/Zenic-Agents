"""
Compatibility adapters: v1 API → v2 agents.

This module provides v1-compatible wrappers around v2 agents so the
orchestrator can use agents without rewriting its call sites.

Every adapter:
  - Delegates to v2 agents internally (execute/run)
  - Exposes the v1 high-level API (classify_with_runner, validate_with_runner, etc.)
  - Translates between v1 schemas (IntentOutput, ValidationOutput, etc.)
    and v2 schemas (IntentResult, SecurityResult, etc.)

Once all orchestrator call sites are migrated to call v2 agents directly,
this module can be deprecated and removed.
"""

from __future__ import annotations

# Re-export adapter classes
from ._adapter import (
    BusinessLogicAgentCompat,
    ReasoningAgentCompat,
    SurgicalAgentCompat,
)

# Re-export mapper classes
from ._mapper import (
    AutomationAgentCompat,
    ValidationAgentCompat,
)

# Re-export migration class
from ._migration import AgentRunnerCompat

# Re-export backward-compatible aliases
from ._types import VALID_GOALS, VALID_OPERATIONS, logger

__all__ = [
    "VALID_GOALS",
    # Backward-compatible aliases
    "VALID_OPERATIONS",
    "AgentRunnerCompat",
    "AutomationAgentCompat",
    "BusinessLogicAgentCompat",
    "ReasoningAgentCompat",
    "SurgicalAgentCompat",
    "ValidationAgentCompat",
    "logger",
]
