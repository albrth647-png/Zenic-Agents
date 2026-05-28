"""
ZENIC-AGENTS - Coordinated Rollback Manager (A3 Rollback Enhancement)

Multi-resource coordinated rollback using SAGA-style compensation.
"""

from src.core.executors.coordinated_rollback._manager import (
    CoordinatedRollbackManager,
    get_coordinated_rollback_manager,
    reset_coordinated_rollback_manager,
)
from src.core.executors.coordinated_rollback._types import (
    ActionStatus,
    CoordinatedAction,
    CoordinatedRollbackResult,
    ResourceRecord,
    ResourceType,
)

__all__ = [
    "ActionStatus",
    "CoordinatedAction",
    "CoordinatedRollbackManager",
    "CoordinatedRollbackResult",
    "ResourceRecord",
    "ResourceType",
    "get_coordinated_rollback_manager",
    "reset_coordinated_rollback_manager",
]
