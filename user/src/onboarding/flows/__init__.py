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

from .base import (
    BaseFlow,
    FlowState,
    FlowResult,
    FlowContext,
    FlowRegistry,
)
from .registration import RegistrationFlow, RegistrationData
from .activation import ActivationFlow, ActivationResult
from .status import StatusFlow, StatusResult
from .hardware import HardwareFlow, HardwareResult

__all__ = [
    # Base
    "BaseFlow",
    "FlowState",
    "FlowResult",
    "FlowContext",
    "FlowRegistry",
    # Flows
    "RegistrationFlow",
    "RegistrationData",
    "ActivationFlow",
    "ActivationResult",
    "StatusFlow",
    "StatusResult",
    "HardwareFlow",
    "HardwareResult",
]
