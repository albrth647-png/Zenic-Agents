from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChaosExperimentState(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FaultType(str, Enum):
    LATENCY = "latency"
    ERROR = "error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DEPENDENCY_FAILURE = "dependency_failure"
    DATA_CORRUPTION = "data_corruption"


@dataclass
class FaultInjection:
    fault_type: FaultType
    target: str
    magnitude: float = 1.0
    duration_seconds: int = 30
    probability: float = 1.0
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosExperiment:
    id: str
    name: str
    description: str = ""
    injections: list[FaultInjection] = field(default_factory=list)
    steady_state_hypothesis: dict[str, Any] = field(default_factory=dict)
    state: ChaosExperimentState = ChaosExperimentState.DRAFT
    scheduled_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    rollback_plan: dict[str, Any] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
