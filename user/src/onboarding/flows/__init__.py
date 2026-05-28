"""
Zenic-Agents — Onboarding Flows Package (Phase 10)

Interactive onboarding flows for end-user registration, license
activation, status checking, and hardware fingerprint display.

Each flow implements the Template Method pattern via BaseFlow,
providing a consistent lifecycle: validate → execute → render → finalize.

Design Patterns:
  - Template Method: BaseFlow defines the algorithm skeleton
  - Strategy: pluggable step strategies per flow type
  - Command: each flow is an executable command object
  - State Machine: flow state transitions (PENDING → RUNNING → COMPLETED/FAILED)
"""

from .activation import ActivationFlow, ActivationResult
from .base import (
    BaseFlow,
    FlowContext,
    FlowRegistry,
    FlowResult,
    FlowState,
)
from .hardware import HardwareFlow, HardwareResult
from .registration import RegistrationData, RegistrationFlow
from .status import StatusFlow, StatusResult

__all__ = [
    "ActivationFlow",
    "ActivationResult",
    # Base
    "BaseFlow",
    "FlowContext",
    "FlowRegistry",
    "FlowResult",
    "FlowState",
    "HardwareFlow",
    "HardwareResult",
    "RegistrationData",
    # Flows
    "RegistrationFlow",
    "StatusFlow",
    "StatusResult",
]
