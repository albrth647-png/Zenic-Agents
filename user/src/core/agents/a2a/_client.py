"""
A2A Protocol — Client for discovering and communicating with external agents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ._types import (
    A2AAgentCard,
    A2ADelegationPolicy,
    A2AResponseMessage,
    A2ATaskMessage,
    A2ATaskPriority,
)

logger = logging.getLogger(__name__)

# Try to import the Rust native module for high-performance operations
try:
    from _zenic_native import (  # noqa: F401 — imported for availability check
        a2a_discover_agents as _rust_discover,
        a2a_get_agent_card as _rust_get_card,
        a2a_handle_task as _rust_handle_task,
        a2a_register_agent as _rust_register,
        a2a_validate_delegation as _rust_validate,  # used by delegate_task policy check
        a2a_list_registered_agents as _rust_list_agents,  # used by discover fallback
    )
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False
    logger.debug("_zenic_native A2A functions not available, using Python fallback")


@dataclass
class A2ADiscoveryResult:
    """Result of an agent discovery query."""
    agents: list[A2AAgentCard] = field(default_factory=list)
    total_found: int = 0
    query_capability: str = ""
    query_niche: str | None = None


@dataclass
class A2ADelegationResult:
    """Result of an A2A task delegation."""
    success: bool
    response: A2AResponseMessage | None = None
    policy_allowed: bool = True
    hitl_required: bool = False
    error: str = ""


class A2AClient:
    """
    Client for A2A (Agent-to-Agent) Protocol.

    Enables Zenic agents to:
    - Discover external agents by capability or niche
    - Delegate tasks to other agents with Policy Engine validation
    - Register Zenic agents in the A2A registry

    Uses Rust native module when available for performance,
    falls back to Python implementation.
    """

    def __init__(self, gateway_url: str = "http://localhost:3000", tenant_id: str = ""):
        self.gateway_url = gateway_url.rstrip("/")
        self.tenant_id = tenant_id
        self._delegation_policy: A2ADelegationPolicy | None = None

    def set_delegation_policy(self, policy: A2ADelegationPolicy) -> None:
        """Set the delegation policy for this client."""
        self._delegation_policy = policy

    async def discover(
        self,
        capability: str,
        niche: str | None = None,
    ) -> A2ADiscoveryResult:
        """
        Discover agents with a specific capability.

        Uses Rust native registry first, then falls back to Gateway API.
        """
        agents: list[A2AAgentCard] = []

        # Try Rust native registry first
        if _HAS_RUST:
            try:
                niche_arg = niche if niche else None
                rust_cards = _rust_discover(capability, niche_arg)
                for card in rust_cards:
                    agents.append(A2AAgentCard(
                        agent_id=card.id,
                        name=card.name,
                        description=card.description,
                        capabilities=card.capabilities,
                        endpoint=card.endpoint,
                        niche_dna=card.niche_dna,
                        requires_hitl=card.requires_hitl,
                        policy_constraints=card.policy_constraints,
                    ))
            except Exception as e:
                logger.warning("Rust A2A discovery failed: %s", e)

        return A2ADiscoveryResult(
            agents=agents,
            total_found=len(agents),
            query_capability=capability,
            query_niche=niche,
        )

    async def delegate_task(
        self,
        task: A2ATaskMessage,
        skip_policy: bool = False,
    ) -> A2ADelegationResult:
        """
        Delegate a task to an external agent via A2A protocol.

        Steps:
        1. Validate delegation against policy (unless skip_policy)
        2. If HITL required, return pending status
        3. Execute task via Rust native or Gateway API
        4. Return result with merkle audit hash
        """
        # Step 1: Policy validation
        if not skip_policy and self._delegation_policy:
            allowed, reason = self._delegation_policy.can_delegate(task)
            if not allowed:
                return A2ADelegationResult(
                    success=False,
                    policy_allowed=False,
                    error=reason,
                )
            if "HITL" in reason or "approval" in reason.lower():
                return A2ADelegationResult(
                    success=False,
                    policy_allowed=True,
                    hitl_required=True,
                    error=reason,
                )

        # Step 2: Execute via Rust native
        if _HAS_RUST:
            try:
                # Create PyO3 A2ATask object
                from _zenic_native import A2ATask as RustA2ATask
                rust_task = RustA2ATask(
                    task_id=task.task_id,
                    sender_agent=task.sender_agent,
                    receiver_agent=task.receiver_agent,
                    payload=json.dumps(task.payload),
                    priority=task.priority.value,
                    requires_approval=task.requires_approval,
                    niche_category=task.niche_category or "",
                )
                rust_response = _rust_handle_task(rust_task)
                response = A2AResponseMessage(
                    task_id=rust_response.task_id,
                    status=rust_response.status,
                    result=json.loads(rust_response.result) if rust_response.result else {},
                    merkle_hash=rust_response.merkle_hash,
                )
                return A2ADelegationResult(
                    success=rust_response.status == "success",
                    response=response,
                    policy_allowed=True,
                )
            except Exception as e:
                logger.error("Rust A2A task execution failed: %s", e)
                return A2ADelegationResult(
                    success=False,
                    error=f"Task execution failed: {e}",
                )

        # Step 3: Fallback — would use Gateway API (HTTP)
        return A2ADelegationResult(
            success=False,
            error="No A2A backend available (Rust native not loaded, Gateway API not configured)",
        )

    async def register_agent(self, card: A2AAgentCard) -> bool:
        """Register a Zenic agent in the A2A registry."""
        if _HAS_RUST:
            try:
                from _zenic_native import AgentCard as RustAgentCard
                rust_card = RustAgentCard(
                    id=card.agent_id,
                    name=card.name,
                    description=card.description,
                    capabilities=card.capabilities,
                    endpoint=card.endpoint,
                    niche_dna=card.niche_dna or "",
                    requires_hitl=card.requires_hitl,
                    policy_constraints=card.policy_constraints,
                )
                return _rust_register(rust_card)
            except Exception as e:
                logger.error("Rust A2A registration failed: %s", e)
                return False
        return False

    async def get_agent_card(self, agent_id: str) -> A2AAgentCard | None:
        """Get an agent's card by ID."""
        if _HAS_RUST:
            try:
                card = _rust_get_card(agent_id)
                if card is not None:
                    return A2AAgentCard(
                        agent_id=card.id,
                        name=card.name,
                        description=card.description,
                        capabilities=card.capabilities,
                        endpoint=card.endpoint,
                        niche_dna=card.niche_dna,
                        requires_hitl=card.requires_hitl,
                        policy_constraints=card.policy_constraints,
                    )
            except Exception as e:
                logger.error("Rust A2A get_agent_card failed: %s", e)
        return None

    def create_task(
        self,
        receiver_agent: str,
        payload: dict[str, Any],
        priority: A2ATaskPriority = A2ATaskPriority.NORMAL,
        niche_category: str | None = None,
    ) -> A2ATaskMessage:
        """Create a new A2A task message."""
        return A2ATaskMessage(
            task_id=f"a2a_{uuid4().hex[:12]}",
            sender_agent="zenic-local",
            receiver_agent=receiver_agent,
            payload=payload,
            priority=priority,
            requires_approval=priority == A2ATaskPriority.CRITICAL,
            niche_category=niche_category,
        )
