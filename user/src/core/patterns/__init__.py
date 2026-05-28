"""
ZENIC-AGENTS - Design Patterns Package

Comprehensive design pattern library for the Zenic-Agents AI code
generation system, optimized for resource-constrained devices
(Android/Termux, 500MB RAM).

All patterns use only Python stdlib — no external dependencies.
All pattern classes are thread-safe.

Organization:

  Creational Patterns
  -------------------
    AgentFactory        — Thread-safe factory for BaseAgent instances
    FactoryRegistry     — Generic named-creator registry
    OrchestratorBuilder — Fluent builder for orchestrator config dicts
    AgentPrototype      — Deep-copy prototype for agent cloning

  Structural Patterns
  -------------------
    LLMAdapter          — ABC for LLM backend adapters
    LocalLLMAdapter     — Wraps MiniAIEngine._call_llm
    FallbackLLMAdapter  — Primary → fallback chain
    AdapterRegistry     — Named LLMAdapter registry
    LLMProvider         — ABC for LLM providers (complete + embed)
    LocalProvider       — Local llama-cpp-python provider
    AgentLLMBridge      — Bridge with hot-swappable provider
    LazyProxy           — Deferred object creation proxy
    CacheProxy          — TTL-based method result cache proxy
    agent_decorator     — Capability-based method decorator factory
    AgentCapability     — Enum of decorator capabilities
    AgentDecorator      — Composable multi-capability decorator

  Behavioral Patterns
  -------------------
    StateMachine        — Thread-safe finite state machine
    State               — State dataclass with entry/exit callbacks
    Transition          — Transition dataclass with guard & action
    StrategyRegistry    — Named strategy registry with defaults
    ASTNode             — ABC for visitable AST nodes
    ASTVisitor          — ABC with double dispatch
    TokenCountVisitor   — Counts AST tokens per node type
    ComplexityVisitor   — Calculates cyclomatic complexity
    RefactorVisitor     — Marks nodes for refactoring
    VisitableAST        — Adapter making ast.AST nodes visitable

  Concurrency Patterns
  --------------------
    WorkerPool          — Dynamic, priority-aware thread pool
    WorkerPoolConfig    — Configuration dataclass for WorkerPool
    ProducerConsumer    — Bounded-buffer producer-consumer
    ReadWriteLock       — RW lock with writer preference (sync + async)

  Resilience Patterns
  -------------------
    CircuitBreaker      — Thread-safe circuit breaker with state machine
    CircuitState        — Enum for CLOSED/OPEN/HALF_OPEN states
    CircuitOpenError    — Exception when circuit is open
    RetryConfig         — Retry configuration dataclass
    retry               — Synchronous retry decorator
    retry_async         — Async retry decorator
    with_retry          — Synchronous retry context manager
    with_retry_async    — Async retry context manager
    RetryScope          — Scoped retry with counting
    Bulkhead            — Concurrency-limited execution with back-pressure
    BulkheadFullError   — Exception when bulkhead is full
    Sidecar             — Cross-cutting concern sidecar pattern
    sidecar_decorator   — Decorator for sidecar actions

  Orchestration Patterns
  ----------------------
    EventBus            — Observer/Pub-Sub for decoupled events
    Event               — Event dataclass
    EventHandler        — ABC for event handlers
    Mediator            — Centralized request/response dispatcher
    Request             — Request dataclass for mediator
    Response            — Response dataclass for mediator
    RequestHandler      — ABC for request handlers
    CommandBus          — Formal Command pattern dispatch
    OrchCommand         — Command dataclass for CommandBus
    OrchCommandHandler  — ABC for command handlers
    CommandResult       — Result dataclass for CommandBus
    Saga                — Multi-step rollback pattern
    SagaStep            — Saga step dataclass
    SagaContext         — Saga execution context
    SagaStatus          — Enum for saga states

  Architectural Patterns
  ----------------------
    CQRSBus             — Command/Query bus with validation & caching
    CQRSCommand         — Write operation dataclass
    Query               — Read operation dataclass
    CQRSCommandHandler  — ABC for command handlers
    QueryHandler        — ABC for query handlers
"""

# ---------------------------------------------------------------------------
# Creational
# ---------------------------------------------------------------------------
from src.core.patterns.architectural import (
    Command as CQRSCommand,
)
from src.core.patterns.architectural import (
    CommandHandler as CQRSCommandHandler,
)

# ---------------------------------------------------------------------------
# Architectural (rename to avoid clash with orchestration Command)
# ---------------------------------------------------------------------------
from src.core.patterns.architectural import (
    CQRSBus,
    Query,
    QueryHandler,
)

# ---------------------------------------------------------------------------
# Behavioral
# ---------------------------------------------------------------------------
from src.core.patterns.behavioral import (
    ASTNode,
    ASTVisitor,
    ComplexityVisitor,
    RefactorVisitor,
    State,
    StateMachine,
    StrategyRegistry,
    TokenCountVisitor,
    Transition,
    VisitableAST,
)

# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------
from src.core.patterns.concurrency import (
    ProducerConsumer,
    ReadWriteLock,
    WorkerPool,
    WorkerPoolConfig,
)
from src.core.patterns.creational import (
    AgentFactory,
    AgentPrototype,
    FactoryRegistry,
    OrchestratorBuilder,
)
from src.core.patterns.orchestration import (
    Command as OrchCommand,
)

# ---------------------------------------------------------------------------
# Orchestration (rename Command/CommandHandler to avoid clash with CQRS)
# ---------------------------------------------------------------------------
from src.core.patterns.orchestration import (
    CommandBus,
    CommandResult,
    Event,
    EventBus,
    EventHandler,
    Mediator,
    Request,
    RequestHandler,
    Response,
    Saga,
    SagaContext,
    SagaStatus,
    SagaStep,
)
from src.core.patterns.orchestration import (
    CommandHandler as OrchCommandHandler,
)

# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------
from src.core.patterns.resilience import (
    Bulkhead,
    BulkheadFullError,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    RetryConfig,
    RetryScope,
    Sidecar,
    retry,
    retry_async,
    sidecar_decorator,
    with_retry,
    with_retry_async,
)

# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------
from src.core.patterns.structural import (
    AdapterRegistry,
    AgentCapability,
    AgentDecorator,
    AgentLLMBridge,
    CacheProxy,
    FallbackLLMAdapter,
    LazyProxy,
    LLMAdapter,
    LLMProvider,
    LocalLLMAdapter,
    LocalProvider,
    agent_decorator,
)

__all__ = [
    "ASTNode",
    "ASTVisitor",
    "AdapterRegistry",
    "AgentCapability",
    "AgentDecorator",
    # Creational
    "AgentFactory",
    "AgentLLMBridge",
    "AgentPrototype",
    "Bulkhead",
    "BulkheadFullError",
    # Architectural
    "CQRSBus",
    "CQRSCommand",
    "CQRSCommandHandler",
    "CacheProxy",
    # Resilience
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "CommandBus",
    "CommandResult",
    "ComplexityVisitor",
    "Event",
    # Orchestration
    "EventBus",
    "EventHandler",
    "FactoryRegistry",
    "FallbackLLMAdapter",
    # Structural
    "LLMAdapter",
    "LLMProvider",
    "LazyProxy",
    "LocalLLMAdapter",
    "LocalProvider",
    "Mediator",
    "OrchCommand",
    "OrchCommandHandler",
    "OrchestratorBuilder",
    "ProducerConsumer",
    "Query",
    "QueryHandler",
    "ReadWriteLock",
    "RefactorVisitor",
    "Request",
    "RequestHandler",
    "Response",
    "RetryConfig",
    "RetryScope",
    "Saga",
    "SagaContext",
    "SagaStatus",
    "SagaStep",
    "Sidecar",
    "State",
    # Behavioral
    "StateMachine",
    "StrategyRegistry",
    "TokenCountVisitor",
    "Transition",
    "VisitableAST",
    # Concurrency
    "WorkerPool",
    "WorkerPoolConfig",
    "agent_decorator",
    "retry",
    "retry_async",
    "sidecar_decorator",
    "with_retry",
    "with_retry_async",
]
