"""
A2A Protocol — Type definitions for Agent-to-Agent communication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class A2ATaskPriority(Enum):
    """Priority levels for A2A tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"  # Requires HITL approval


@dataclass
class A2AAgentCard:
    """Agent Card describing an A2A agent's capabilities."""

    agent_id: str
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    endpoint: str = ""
    niche_dna: str | None = None
    requires_hitl: bool = False
    policy_constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "niche_dna": self.niche_dna,
            "requires_hitl": self.requires_hitl,
            "policy_constraints": self.policy_constraints,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AAgentCard:
        return cls(
            agent_id=data.get("agent_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            endpoint=data.get("endpoint", ""),
            niche_dna=data.get("niche_dna"),
            requires_hitl=data.get("requires_hitl", False),
            policy_constraints=data.get("policy_constraints", []),
        )


@dataclass
class A2ATaskMessage:
    """A2A task message for cross-agent communication."""

    task_id: str
    sender_agent: str
    receiver_agent: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: A2ATaskPriority = A2ATaskPriority.NORMAL
    requires_approval: bool = False
    niche_category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "sender_agent": self.sender_agent,
            "receiver_agent": self.receiver_agent,
            "payload": self.payload,
            "priority": self.priority.value,
            "requires_approval": self.requires_approval,
            "niche_category": self.niche_category,
        }


@dataclass
class A2AResponseMessage:
    """Response from an A2A task execution."""

    task_id: str
    status: str  # "success", "denied", "error", "pending_approval"
    result: dict[str, Any] = field(default_factory=dict)
    merkle_hash: str = ""  # Audit trail hash

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AResponseMessage:
        return cls(
            task_id=data.get("task_id", ""),
            status=data.get("status", "error"),
            result=data.get("result", {}),
            merkle_hash=data.get("merkle_hash", ""),
        )


@dataclass
class A2ADelegationPolicy:
    """Policy rules for A2A task delegation."""

    allowed_agents: list[str] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    blocked_agents: list[str] = field(default_factory=list)
    max_priority: A2ATaskPriority = A2ATaskPriority.HIGH
    require_hitl_for_critical: bool = True
    allowed_niches: list[str] = field(default_factory=list)

    def can_delegate(self, task: A2ATaskMessage) -> tuple[bool, str]:
        """Check if a delegation is allowed by this policy."""
        if task.receiver_agent in self.blocked_agents:
            return False, f"Agent {task.receiver_agent} is blocked"
        if self.allowed_agents and task.receiver_agent not in self.allowed_agents:
            return False, f"Agent {task.receiver_agent} not in allowed list"
        priority_order = [A2ATaskPriority.LOW, A2ATaskPriority.NORMAL, A2ATaskPriority.HIGH, A2ATaskPriority.CRITICAL]
        if priority_order.index(task.priority) > priority_order.index(self.max_priority):
            return False, f"Priority {task.priority.value} exceeds max allowed {self.max_priority.value}"
        if task.priority == A2ATaskPriority.CRITICAL and self.require_hitl_for_critical:
            return True, "Requires HITL approval for critical task"
        return True, "Allowed"
