"""
A2A Protocol — Agent-to-Agent Interoperability Client

Enables Zenic agents to discover and communicate with external agents
using the Google A2A protocol. Integrates with Policy Engine and HITL
for governance of cross-agent delegations.
"""

from ._client import A2AClient, A2ADiscoveryResult, A2ADelegationResult
from ._types import (
    A2AAgentCard,
    A2ATaskMessage,
    A2ATaskPriority,
    A2AResponseMessage,
    A2ADelegationPolicy,
)

__all__ = [
    "A2AClient",
    "A2ADelegationPolicy",
    "A2ADelegationResult",
    "A2ADiscoveryResult",
    "A2AAgentCard",
    "A2AResponseMessage",
    "A2ATaskMessage",
    "A2ATaskPriority",
]
