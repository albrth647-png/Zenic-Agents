"""
ZENIC-AGENTS - Orchestration Patterns (Facade Module)

Re-exports all orchestration pattern components from their dedicated
sub-modules for convenient unified imports.

Pattern Catalog:
- EventBus: Observer/Pub-Sub pattern for decoupled event-driven communication
- Mediator: Centralized request/response dispatcher for agent coordination
- CommandBus: Formal Command pattern replacing if/elif dispatch chains
- Saga: Multi-step rollback pattern for distributed operations

Usage::

    from src.core.patterns.orchestration import EventBus, Event, EventHandler
    from src.core.patterns.orchestration import Mediator, Request, Response
    from src.core.patterns.orchestration import CommandBus, Command, CommandResult
    from src.core.patterns.orchestration import Saga, SagaStep, SagaContext

Designed for resource-constrained environments (Android/Termux, 500MB RAM).
No external dependencies beyond Python stdlib.
"""

# ============================================================
#  EVENT BUS - Observer/Pub-Sub Pattern
# ============================================================

# ============================================================
#  COMMAND BUS - Command Pattern
# ============================================================
from .command_bus import (
    Command,
    CommandBus,
    CommandHandler,
    CommandResult,
)
from .event_bus import (
    Event,
    EventBus,
    EventHandler,
)

# ============================================================
#  MEDIATOR - Agent Coordination Pattern
# ============================================================
from .mediator import (
    Mediator,
    Request,
    RequestHandler,
    Response,
)

# ============================================================
#  SAGA - Multi-Step Rollback Pattern
# ============================================================
from .saga import (
    Saga,
    SagaContext,
    SagaStatus,
    SagaStep,
)

# ============================================================
#  PUBLIC API
# ============================================================

__all__ = [
    "Command",
    # Command Bus
    "CommandBus",
    "CommandHandler",
    "CommandResult",
    "Event",
    # Event Bus
    "EventBus",
    "EventHandler",
    # Mediator
    "Mediator",
    "Request",
    "RequestHandler",
    "Response",
    # Saga
    "Saga",
    "SagaContext",
    "SagaStatus",
    "SagaStep",
]
