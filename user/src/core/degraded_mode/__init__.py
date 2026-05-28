"""
Zenic-Agents Asistente - Degraded Mode Package (Phase 6.4)

System operating modes based on license and security state.

Modes:
- NORMAL: Full functionality
- DEGRADED: Limited features (no executors, read-only dashboards)
- PARALYSIS L1: Read-only mode (only viewing, no modifications)
- PARALYSIS L2: Emergency lockdown (admin-only access)
"""

from .manager import (
    DegradedModeManager,
    ModeTransition,
    SystemMode,
    get_degraded_mode_manager,
    reset_degraded_mode_manager,
)
from .mode_parts.capabilities import (
    MODE_CAPABILITIES,
    ModeCapabilities,
)
from .persistence import DegradationPersistence
from .types import (
    DegradationLevel,
    DegradationReason,
    DegradationState,
)

__all__ = [
    "MODE_CAPABILITIES",
    # Types
    "DegradationLevel",
    # Persistence
    "DegradationPersistence",
    "DegradationReason",
    "DegradationState",
    # Manager
    "DegradedModeManager",
    "ModeCapabilities",
    "ModeTransition",
    "SystemMode",
    # Singleton helpers
    "get_degraded_mode_manager",
    "reset_degraded_mode_manager",
]
