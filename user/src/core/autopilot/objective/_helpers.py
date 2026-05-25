"""
ZENIC-AGENTS — Objective Helpers

Utility functions for objective operations: factory constructors,
validation, progress summarization, and deadline calculations.

These helpers reduce boilerplate when creating and validating
Objective and ObjectiveTarget instances, and provide aggregate
analytics across multiple objectives.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ._scoring import Objective, ObjectivePriority, ObjectiveStatus, ObjectiveTarget

# ── ID Generation ───────────────────────────────────────────


def generate_objective_id() -> str:
    """Generate a unique objective ID with ``obj-`` prefix.

    Uses ``uuid.uuid4`` for cryptographic randomness.

    Returns:
        A string like ``obj-a1b2c3d4e5f6``.
    """
    return f"obj-{uuid.uuid4().hex[:12]}"


# ── Timestamps ──────────────────────────────────────────────


def now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format.

    Returns:
        ISO format string, e.g. ``2026-05-26T14:30:00+00:00``.
    """
    return datetime.now(timezone.utc).isoformat()


# ── Factory Constructors ────────────────────────────────────


def create_target(
    metric_name: str,
    current_value: float,
    target_value: float,
    operator: str = "<",
    unit: str = "",
) -> ObjectiveTarget:
    """Convenience factory for creating an ObjectiveTarget.

    Args:
        metric_name: Name of the metric to track.
        current_value: Current metric value.
        target_value: Desired metric value.
        operator: Comparison operator (``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``).
        unit: Optional unit label, e.g. ``"%"``, ``"USD"``.

    Returns:
        A new ObjectiveTarget instance.
    """
    return ObjectiveTarget(
        metric_name=metric_name,
        current_value=current_value,
        target_value=target_value,
        unit=unit,
        operator=operator,
    )


def create_objective(
    name: str,
    metric_name: str,
    current_value: float,
    target_value: float,
    operator: str = "<",
    unit: str = "",
    priority: ObjectivePriority = ObjectivePriority.NORMAL,
    deadline: str = "",
    tenant_id: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Objective:
    """Convenience factory for creating an Objective with a single target.

    Creates an Objective in DRAFT status with one ObjectiveTarget.
    Use ``objective_store.create_objective()`` to persist it.

    Args:
        name: Human-readable objective name.
        metric_name: Name of the metric to track.
        current_value: Current metric value.
        target_value: Desired metric value.
        operator: Comparison operator for the target.
        unit: Optional unit label.
        priority: Objective priority level.
        deadline: ISO 8601 deadline string (empty = no deadline).
        tenant_id: Tenant identifier (empty = global).
        tags: Optional list of tag strings.
        metadata: Optional dict of extra metadata.

    Returns:
        A new Objective instance in DRAFT status.
    """
    target = create_target(
        metric_name=metric_name,
        current_value=current_value,
        target_value=target_value,
        operator=operator,
        unit=unit,
    )
    return Objective(
        name=name,
        priority=priority,
        status=ObjectiveStatus.DRAFT,
        targets=[target],
        deadline=deadline,
        tenant_id=tenant_id,
        tags=tags or [],
        metadata=metadata or {},
    )


# ── Status Checks ───────────────────────────────────────────


def is_terminal_status(status: ObjectiveStatus) -> bool:
    """Check if the status is terminal (no further transitions allowed).

    Terminal statuses: COMPLETED, FAILED, CANCELLED.

    Args:
        status: The status to check.

    Returns:
        True if the status is terminal.
    """
    return status in (
        ObjectiveStatus.COMPLETED,
        ObjectiveStatus.FAILED,
        ObjectiveStatus.CANCELLED,
    )


# ── Validation ──────────────────────────────────────────────


def validate_target(target: ObjectiveTarget) -> list[str]:
    """Validate an ObjectiveTarget and return list of error messages.

    Checks: non-empty metric_name, valid operator, numeric values.

    Args:
        target: The ObjectiveTarget to validate.

    Returns:
        Empty list if valid, list of error message strings otherwise.
    """
    errors: list[str] = []

    if not target.metric_name.strip():
        errors.append("metric_name must be non-empty")

    valid_operators = {"<", ">", "<=", ">=", "==", "!="}
    if target.operator not in valid_operators:
        errors.append(
            f"Invalid operator '{target.operator}'. "
            f"Must be one of: {', '.join(sorted(valid_operators))}"
        )

    if not isinstance(target.current_value, (int, float)):
        errors.append("current_value must be numeric")

    if not isinstance(target.target_value, (int, float)):
        errors.append("target_value must be numeric")

    return errors


def validate_objective(objective: Objective) -> list[str]:
    """Validate an Objective's fields and return list of error messages.

    Checks: name non-empty, at least one target, valid targets,
    valid deadline format if provided.

    Args:
        objective: The Objective to validate.

    Returns:
        Empty list if valid, list of error message strings otherwise.
    """
    errors: list[str] = []

    if not objective.name.strip():
        errors.append("name must be non-empty")

    if not objective.targets:
        errors.append("At least one target is required")
    else:
        for i, target in enumerate(objective.targets):
            target_errors = validate_target(target)
            for err in target_errors:
                errors.append(f"Target[{i}]: {err}")

    if objective.deadline:
        parsed = parse_deadline(objective.deadline)
        if parsed is None:
            errors.append(
                f"Invalid deadline format: '{objective.deadline}'. "
                "Expected ISO 8601 format."
            )

    return errors


# ── Aggregate Analytics ─────────────────────────────────────


def compute_progress_summary(objectives: list[Objective]) -> dict[str, Any]:
    """Compute aggregate progress statistics across multiple objectives.

    Useful for dashboard displays and KPI reporting.

    Args:
        objectives: List of Objective instances to summarize.

    Returns:
        Dictionary with keys: total, active, completed, failed,
        overdue, avg_progress.
    """
    if not objectives:
        return {
            "total": 0,
            "active": 0,
            "completed": 0,
            "failed": 0,
            "overdue": 0,
            "avg_progress": 0.0,
        }

    active = sum(1 for o in objectives if o.status == ObjectiveStatus.ACTIVE)
    completed = sum(1 for o in objectives if o.status == ObjectiveStatus.COMPLETED)
    failed = sum(1 for o in objectives if o.status == ObjectiveStatus.FAILED)
    overdue = sum(1 for o in objectives if o.is_overdue())
    progresses = [o.progress_percent() for o in objectives]
    avg_progress = round(sum(progresses) / len(progresses), 2) if progresses else 0.0

    return {
        "total": len(objectives),
        "active": active,
        "completed": completed,
        "failed": failed,
        "overdue": overdue,
        "avg_progress": avg_progress,
    }


# ── Deadline Utilities ──────────────────────────────────────


def parse_deadline(deadline_str: str) -> datetime | None:
    """Safely parse a deadline ISO string, returning None on failure.

    Args:
        deadline_str: ISO 8601 datetime string.

    Returns:
        A datetime object or None if parsing fails.
    """
    if not deadline_str:
        return None
    try:
        return datetime.fromisoformat(deadline_str)
    except (ValueError, TypeError):
        return None


def days_until_deadline(deadline: str) -> float | None:
    """Calculate days remaining until deadline.

    Returns None if no deadline or parse error. Returns a negative
    value if the deadline has already passed.

    Args:
        deadline: ISO 8601 deadline string.

    Returns:
        Days remaining (float) or None.
    """
    parsed = parse_deadline(deadline)
    if parsed is None:
        return None
    now = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = parsed - now
    return delta.total_seconds() / 86400.0


# ── Public Exports ──────────────────────────────────────────

__all__ = [
    "compute_progress_summary",
    "create_objective",
    "create_target",
    "days_until_deadline",
    "generate_objective_id",
    "is_terminal_status",
    "now_iso",
    "parse_deadline",
    "validate_objective",
    "validate_target",
]
