"""
automation_parts — Sub-modules for AutomationEngine.

Re-exports all public symbols for convenient access.
"""

from .engine import AutomationEngine
from .types import (
    DB_DIR,
    DB_PATH,
    PROJECTS_DIR,
    Action,
    ActionType,
    Trigger,
    TriggerType,
    Workflow,
    WorkflowExecution,
)

__all__ = [
    # Constants
    "DB_DIR",
    "DB_PATH",
    "PROJECTS_DIR",
    "Action",
    "ActionType",
    # Main class
    "AutomationEngine",
    # Dataclasses
    "Trigger",
    # Enums
    "TriggerType",
    "Workflow",
    "WorkflowExecution",
]
