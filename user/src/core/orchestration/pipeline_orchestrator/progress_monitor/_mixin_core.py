"""Core logic for progress_monitor."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class _PipelineProgress:
    """Internal pipeline progress tracker."""

    __slots__ = (
        "completed_steps",
        "current_step",
        "failed_steps",
        "finished_at",
        "pipeline_id",
        "skipped_steps",
        "started_at",
        "status",
        "step_states",
        "step_weights",
        "total_steps",
    )

    def __init__(
        self,
        pipeline_id: str,
        total_steps: int = 0,
        step_weights: dict[str, float] | None = None,
        started_at: float | None = None,
    ) -> None:
        self.pipeline_id = pipeline_id
        self.total_steps = total_steps
        self.completed_steps = 0
        self.failed_steps = 0
        self.skipped_steps = 0
        self.current_step = ""
        self.step_states: dict[str, _StepProgress] = {}  # noqa: F821
        self.step_weights = step_weights or {}
        self.started_at = started_at
        self.finished_at: float | None = None
        self.status = ProgressStatus.RUNNING  # noqa: F821  # TODO: Phase3 - verify import
