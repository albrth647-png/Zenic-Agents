"""
Zenic-Agents — Base Flow with Template Method Pattern (Phase 10)

Defines the algorithm skeleton for all onboarding flows:
  validate() → execute() → render() → finalize()

Subclasses override individual steps while the base class
controls the overall lifecycle and state transitions.

Design Patterns:
  - Template Method: on_run() calls steps in fixed order
  - State Machine: FlowState enum tracks lifecycle
  - Command: each flow is an executable command
  - Registry: FlowRegistry for flow discovery
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type


logger = logging.getLogger(__name__)


# ── Flow State Machine ───────────────────────────────────────

class FlowState(str, Enum):
    """Lifecycle states for an onboarding flow.

    Transitions:
        PENDING → RUNNING → COMPLETED
                           → FAILED
                           → CANCELLED
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if this state is terminal (no further transitions)."""
        return self in (FlowState.COMPLETED, FlowState.FAILED, FlowState.CANCELLED)

    def is_active(self) -> bool:
        """Check if this state represents an active flow."""
        return self in (FlowState.PENDING, FlowState.RUNNING)


# ── Data Types ───────────────────────────────────────────────

@dataclass
class FlowResult:
    """Result of a flow execution.

    Attributes:
        success: Whether the flow completed successfully.
        state: Final state of the flow.
        data: Result data from the flow execution.
        message: Human-readable result message.
        errors: List of error messages if the flow failed.
        elapsed_ms: Execution time in milliseconds.
        flow_id: Unique identifier for this flow execution.
        flow_name: Name of the flow that was executed.
    """
    success: bool
    state: FlowState
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    errors: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    flow_id: str = ""
    flow_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "success": self.success,
            "state": self.state.value,
            "data": self.data,
            "message": self.message,
            "errors": self.errors,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
        }


@dataclass
class FlowContext:
    """Shared context passed between flow steps.

    Acts as a bag for carrying data between the validate → execute →
    render → finalize pipeline steps. Each step can read and write
    to the context.

    Attributes:
        flow_id: Unique execution ID.
        user_input: Raw user input for the flow.
        env: Environment variables / configuration.
        artifacts: Collected artifacts from each step.
    """
    flow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_input: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def set_artifact(self, key: str, value: Any) -> None:
        """Store an artifact in the context."""
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Retrieve an artifact from the context."""
        return self.artifacts.get(key, default)

    def get_input(self, key: str, default: str = "") -> str:
        """Get a user input value."""
        return str(self.user_input.get(key, default))


# ── Base Flow (Template Method) ──────────────────────────────

class BaseFlow(ABC):
    """Abstract base for all onboarding flows using Template Method.

    The algorithm skeleton is:
        1. on_validate()  — validate inputs
        2. on_execute()   — perform the core operation
        3. on_render()    — format output for display
        4. on_finalize()  — cleanup / side effects

    Subclasses MUST implement on_execute() and MAY override
    the other steps for custom behavior.

    Usage::

        class MyFlow(BaseFlow):
            name = "my_flow"
            description = "Does something cool"

            def on_validate(self, ctx: FlowContext) -> None:
                if not ctx.get_input("key"):
                    raise ValueError("Key is required")

            def on_execute(self, ctx: FlowContext) -> None:
                ctx.set_artifact("result", "done")

            def on_render(self, ctx: FlowContext) -> str:
                return f"Result: {ctx.get_artifact('result')}"

    State Transitions:
        PENDING → RUNNING → COMPLETED (on success)
                           → FAILED     (on exception)
                           → CANCELLED  (on CancelledError)
    """

    # Class-level metadata (overridden by subclasses)
    name: str = "base"
    description: str = "Base onboarding flow"
    version: str = "1.0.0"

    def __init__(self) -> None:
        self._state: FlowState = FlowState.PENDING
        self._context: FlowContext = FlowContext()
        self._started_at: float = 0.0
        self._result: Optional[FlowResult] = None
        self._hooks: Dict[str, List[Callable[..., None]]] = {
            "pre_validate": [],
            "post_validate": [],
            "pre_execute": [],
            "post_execute": [],
            "pre_render": [],
            "post_render": [],
            "on_complete": [],
            "on_fail": [],
        }

    # ── Properties ───────────────────────────────────────────

    @property
    def state(self) -> FlowState:
        return self._state

    @property
    def context(self) -> FlowContext:
        return self._context

    @property
    def result(self) -> Optional[FlowResult]:
        return self._result

    # ── Hook System ──────────────────────────────────────────

    def add_hook(self, event: str, callback: Callable[..., None]) -> None:
        """Register a lifecycle hook callback.

        Available events: pre_validate, post_validate, pre_execute,
        post_execute, pre_render, post_render, on_complete, on_fail
        """
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _fire_hooks(self, event: str, **kwargs: Any) -> None:
        """Fire all registered hooks for an event."""
        for callback in self._hooks.get(event, []):
            try:
                callback(**kwargs)
            except Exception as exc:
                logger.warning("Hook %s error: %s", event, exc)

    # ── Template Method ──────────────────────────────────────

    def run(self, user_input: Optional[Dict[str, Any]] = None,
            env: Optional[Dict[str, str]] = None) -> FlowResult:
        """Execute the flow with the Template Method pattern.

        This is the main entry point — it orchestrates the full
        lifecycle: validate → execute → render → finalize.

        Args:
            user_input: Dictionary of user-provided inputs.
            env: Environment variables / configuration.

        Returns:
            FlowResult with success/failure status and output data.
        """
        self._context = FlowContext(
            user_input=user_input or {},
            env=env or {},
        )
        self._state = FlowState.RUNNING
        self._started_at = time.monotonic()
        errors: List[str] = []
        rendered_output = ""

        try:
            # Step 1: Validate
            self._fire_hooks("pre_validate", context=self._context)
            self.on_validate(self._context)
            self._fire_hooks("post_validate", context=self._context)

            # Step 2: Execute
            self._fire_hooks("pre_execute", context=self._context)
            self.on_execute(self._context)
            self._fire_hooks("post_execute", context=self._context)

            # Step 3: Render
            self._fire_hooks("pre_render", context=self._context)
            rendered_output = self.on_render(self._context)
            self._fire_hooks("post_render", context=self._context)

            # Step 4: Finalize
            self.on_finalize(self._context)

            # Success
            self._state = FlowState.COMPLETED
            self._fire_hooks("on_complete", context=self._context)

        except KeyboardInterrupt:
            self._state = FlowState.CANCELLED
            errors.append("Flow cancelled by user")

        except Exception as exc:
            self._state = FlowState.FAILED
            errors.append(str(exc))
            self._fire_hooks("on_fail", context=self._context, error=exc)
            logger.error("Flow %s failed: %s", self.name, exc)

        elapsed = (time.monotonic() - self._started_at) * 1000

        self._result = FlowResult(
            success=self._state == FlowState.COMPLETED,
            state=self._state,
            data=self._context.artifacts,
            message=rendered_output,
            errors=errors,
            elapsed_ms=elapsed,
            flow_id=self._context.flow_id,
            flow_name=self.name,
        )

        return self._result

    # ── Overridable Steps ────────────────────────────────────

    def on_validate(self, ctx: FlowContext) -> None:
        """Validate user inputs before execution. Override for custom validation.

        Raises:
            ValueError: If validation fails.
        """
        pass

    @abstractmethod
    def on_execute(self, ctx: FlowContext) -> None:
        """Execute the core flow logic. MUST be implemented by subclasses.

        Store results in ctx.set_artifact() for the render step.
        """
        ...

    def on_render(self, ctx: FlowContext) -> str:
        """Render the flow output for display. Override for custom formatting.

        Returns:
            Formatted string output for display.
        """
        return f"Flow '{self.name}' completed successfully."

    def on_finalize(self, ctx: FlowContext) -> None:
        """Cleanup and side effects after execution. Override for custom cleanup."""
        pass


# ── Flow Registry ────────────────────────────────────────────

class FlowRegistry:
    """Registry of available onboarding flows.

    Implements the Registry pattern for flow discovery.
    Flows are registered by name and can be instantiated on demand.

    Usage::

        registry = FlowRegistry()
        registry.register("activation", ActivationFlow)
        flow = registry.create("activation")
        result = flow.run(user_input={"key": "ZENIC-..."})
    """

    def __init__(self) -> None:
        self._flows: Dict[str, Type[BaseFlow]] = {}

    def register(self, name: str, flow_class: Type[BaseFlow]) -> None:
        """Register a flow class by name."""
        self._flows[name] = flow_class
        logger.debug("FlowRegistry: Registered flow '%s'", name)

    def unregister(self, name: str) -> None:
        """Unregister a flow by name."""
        self._flows.pop(name, None)

    def create(self, name: str) -> BaseFlow:
        """Create a new flow instance by name.

        Raises:
            KeyError: If the flow name is not registered.
        """
        if name not in self._flows:
            raise KeyError(f"Flow '{name}' not registered. Available: {list(self._flows.keys())}")
        return self._flows[name]()

    def list_flows(self) -> List[Dict[str, str]]:
        """List all registered flows with metadata."""
        result = []
        for name, flow_class in self._flows.items():
            instance = flow_class()
            result.append({
                "name": name,
                "description": instance.description,
                "version": instance.version,
            })
        return result

    @property
    def flow_names(self) -> List[str]:
        """Get list of registered flow names."""
        return list(self._flows.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._flows

    def __len__(self) -> int:
        return len(self._flows)
