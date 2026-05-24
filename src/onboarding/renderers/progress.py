"""
Zenic-Agents — Progress Renderer (Phase 10)

Step-based progress indicators for multi-step onboarding flows.
Supports Rich spinners, step checklists, and plain-text fallbacks.

Design Patterns:
  - Observer: step callbacks for progress updates
  - Value Object: StepIndicator as immutable step descriptor
  - Flyweight: shared console instance
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

try:
    from rich.box import ROUNDED  # noqa: F401
    from rich.console import Console
    from rich.panel import Panel  # noqa: F401
    from rich.text import Text  # noqa: F401

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Step Status ──────────────────────────────────────────────


class StepStatus(str, Enum):
    """Status of a single onboarding step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def icon(self) -> str:
        """Get the status icon for display."""
        icons = {
            StepStatus.PENDING: "\u25cb",  # ○
            StepStatus.RUNNING: "\u25cf",  # ● (animated in Rich)
            StepStatus.COMPLETED: "\u2713",  # ✓
            StepStatus.FAILED: "\u2717",  # ✗
            StepStatus.SKIPPED: "\u2298",  # ⊘
        }
        return icons.get(self, "?")

    @property
    def rich_style(self) -> str:
        """Get the Rich style for this status."""
        styles = {
            StepStatus.PENDING: "dim",
            StepStatus.RUNNING: "bold yellow",
            StepStatus.COMPLETED: "bold green",
            StepStatus.FAILED: "bold red",
            StepStatus.SKIPPED: "dim",
        }
        return styles.get(self, "white")


# ── Step Indicator ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StepIndicator:
    """Describes a single step in the onboarding progress.

    Attributes:
        name: Step identifier.
        label: Human-readable step description.
        status: Current step status.
        started_at: Timestamp when the step started.
        completed_at: Timestamp when the step completed.
        error_message: Error message if the step failed.
    """

    name: str
    label: str
    status: StepStatus = StepStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    error_message: str = ""

    @property
    def duration_ms(self) -> float:
        """Get the step duration in milliseconds."""
        if self.started_at == 0:
            return 0.0
        end = self.completed_at or time.monotonic()
        return (end - self.started_at) * 1000


# ── Progress Renderer ────────────────────────────────────────


class ProgressRenderer:
    """Renders multi-step progress indicators for onboarding flows.

    Tracks the state of each step and renders a checklist-style
    progress display showing which steps are complete, running,
    pending, or failed.

    Usage::

        renderer = ProgressRenderer()
        renderer.add_step("validate", "Validating inputs")
        renderer.add_step("activate", "Activating license")
        renderer.add_step("verify", "Verifying activation")
        renderer.start_step("validate")
        # ... do validation ...
        renderer.complete_step("validate")
        renderer.start_step("activate")
        # ... do activation ...
        output = renderer.render()
    """

    def __init__(self, title: str = "Progress") -> None:
        self._title = title
        self._steps: dict[str, StepIndicator] = {}
        self._step_order: list[str] = []
        self._callbacks: list[Callable[[StepIndicator], None]] = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def steps(self) -> list[StepIndicator]:
        """Get all steps in order."""
        return [self._steps[name] for name in self._step_order if name in self._steps]

    @property
    def completed_count(self) -> int:
        """Count of completed steps."""
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def total_count(self) -> int:
        """Total number of steps."""
        return len(self._steps)

    @property
    def progress_percent(self) -> float:
        """Progress as a percentage (0-100)."""
        if not self._steps:
            return 0.0
        return (self.completed_count / self.total_count) * 100

    @property
    def is_complete(self) -> bool:
        """Whether all steps are completed or skipped."""
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    @property
    def has_failure(self) -> bool:
        """Whether any step has failed."""
        return any(s.status == StepStatus.FAILED for s in self.steps)

    # ── Step Management ──────────────────────────────────────

    def add_step(self, name: str, label: str) -> ProgressRenderer:
        """Add a step to the progress tracker (fluent API)."""
        self._steps[name] = StepIndicator(name=name, label=label)
        self._step_order.append(name)
        return self

    def start_step(self, name: str) -> None:
        """Mark a step as running."""
        if name in self._steps:
            old = self._steps[name]
            self._steps[name] = StepIndicator(
                name=old.name,
                label=old.label,
                status=StepStatus.RUNNING,
                started_at=time.monotonic(),
            )
            self._notify(self._steps[name])

    def complete_step(self, name: str) -> None:
        """Mark a step as completed."""
        if name in self._steps:
            old = self._steps[name]
            self._steps[name] = StepIndicator(
                name=old.name,
                label=old.label,
                status=StepStatus.COMPLETED,
                started_at=old.started_at or time.monotonic(),
                completed_at=time.monotonic(),
            )
            self._notify(self._steps[name])

    def fail_step(self, name: str, error: str = "") -> None:
        """Mark a step as failed."""
        if name in self._steps:
            old = self._steps[name]
            self._steps[name] = StepIndicator(
                name=old.name,
                label=old.label,
                status=StepStatus.FAILED,
                started_at=old.started_at,
                completed_at=time.monotonic(),
                error_message=error,
            )
            self._notify(self._steps[name])

    def skip_step(self, name: str) -> None:
        """Mark a step as skipped."""
        if name in self._steps:
            old = self._steps[name]
            self._steps[name] = StepIndicator(
                name=old.name,
                label=old.label,
                status=StepStatus.SKIPPED,
                started_at=old.started_at,
                completed_at=time.monotonic(),
            )

    # ── Callbacks ────────────────────────────────────────────

    def on_step_change(self, callback: Callable[[StepIndicator], None]) -> None:
        """Register a callback for step status changes."""
        self._callbacks.append(callback)

    def _notify(self, step: StepIndicator) -> None:
        """Notify all registered callbacks."""
        for cb in self._callbacks:
            try:
                cb(step)
            except Exception:
                pass

    # ── Rendering ────────────────────────────────────────────

    def render(self) -> str:
        """Render the progress display."""
        if HAS_RICH:
            return self._render_rich()
        return self._render_plain()

    def _render_rich(self) -> str:
        """Render with Rich formatting."""
        import io

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=60)

        # Progress bar
        bar_width = 30
        filled = int(bar_width * self.progress_percent / 100)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        console.print(f"  [{bar}] {self.progress_percent:.0f}%", style="bold")

        # Step checklist
        for step in self.steps:
            icon = step.status.icon
            style = step.status.rich_style
            duration = ""
            if step.duration_ms > 0:
                duration = f" [dim]({step.duration_ms:.0f}ms)[/]"

            error = ""
            if step.error_message:
                error = f"\n    [red]{step.error_message}[/]"

            console.print(f"  {icon} {step.label}{duration}{error}", style=style)

        return buf.getvalue()

    def _render_plain(self) -> str:
        """Render as plain text."""
        lines = []
        bar_width = 30
        filled = int(bar_width * self.progress_percent / 100)
        bar = "#" * filled + "-" * (bar_width - filled)
        lines.append(f"  [{bar}] {self.progress_percent:.0f}%")

        for step in self.steps:
            icon = step.status.icon
            duration = f" ({step.duration_ms:.0f}ms)" if step.duration_ms > 0 else ""
            error = f"\n    ERROR: {step.error_message}" if step.error_message else ""
            lines.append(f"  {icon} {step.label}{duration}{error}")

        return "\n".join(lines)


# ── Convenience Function ────────────────────────────────────


def render_progress(title: str = "Progress", steps: list[tuple] | None = None) -> str:
    """One-shot progress rendering with step tuples.

    Args:
        title: Progress panel title.
        steps: List of (name, label, status) tuples.

    Returns:
        Formatted progress display string.
    """
    renderer = ProgressRenderer(title=title)
    if steps:
        for name, label, status in steps:
            renderer.add_step(name, label)
            if status == "completed":
                renderer.complete_step(name)
            elif status == "failed":
                renderer.fail_step(name)
            elif status == "running":
                renderer.start_step(name)
            elif status == "skipped":
                renderer.skip_step(name)
    return renderer.render()
