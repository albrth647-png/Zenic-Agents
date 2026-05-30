"""
NicheOnboardingPipeline — Pipeline Steps and State (Phase D).

Defines the pipeline step identifiers and mutable state container
for the niche onboarding pipeline.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...executors.safety_gate.domain_gate import DomainSafetyCheckResult
    from ...niche_rust.certifier_bridge import CertificationResultPy

# ──────────────────────────────────────────────────────────────
# PIPELINE STEPS
# ──────────────────────────────────────────────────────────────


class PipelineStep(str, Enum):
    """Pipeline step identifiers."""

    NOT_STARTED = "not_started"
    SELECT_NICHE = "select_niche"
    UPLOAD_DOCUMENTS = "upload_documents"
    GENERATE_QUESTIONS = "generate_questions"
    COLLECT_ANSWERS = "collect_answers"
    VALIDATE_TEMPLATE = "validate_template"
    SAFETY_CHECK = "safety_check"
    CERTIFY_BLUEPRINT = "certify_blueprint"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────
# PIPELINE STATE
# ──────────────────────────────────────────────────────────────


class PipelineState:
    """Mutable state for an ongoing pipeline execution."""

    __slots__ = (
        "cert_result",
        "created_at",
        "current_step",
        "documents_ingested",
        "errors",
        "fields_auto_filled",
        "fields_manual_filled",
        "niche_category",
        "niche_id",
        "pipeline_id",
        "questions",
        "required_fields",
        "safety_result",
        "session_id",
        "template_dict",
        "total_fields",
        "updated_at",
        "warnings",
    )

    def __init__(self, niche_id: str = "") -> None:
        self.pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
        self.niche_id = niche_id
        self.niche_category = ""
        self.current_step = PipelineStep.NOT_STARTED
        self.template_dict: dict[str, Any] | None = None
        self.session_id = ""
        self.documents_ingested = 0
        self.fields_auto_filled = 0
        self.fields_manual_filled = 0
        self.total_fields = 0
        self.required_fields = 0
        self.questions: list[dict[str, Any]] = []
        self.safety_result: DomainSafetyCheckResult | None = None
        self.cert_result: CertificationResultPy | None = None
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.created_at = time.time()
        self.updated_at = time.time()

    def advance(self, step: PipelineStep) -> None:
        self.current_step = step
        self.updated_at = time.time()

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.updated_at = time.time()

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        self.updated_at = time.time()

    def progress_pct(self) -> float:
        """Calculate overall pipeline progress (0-100)."""
        step_values = {
            PipelineStep.NOT_STARTED: 0,
            PipelineStep.SELECT_NICHE: 12.5,
            PipelineStep.UPLOAD_DOCUMENTS: 25.0,
            PipelineStep.GENERATE_QUESTIONS: 37.5,
            PipelineStep.COLLECT_ANSWERS: 50.0,
            PipelineStep.VALIDATE_TEMPLATE: 62.5,
            PipelineStep.SAFETY_CHECK: 75.0,
            PipelineStep.CERTIFY_BLUEPRINT: 87.5,
            PipelineStep.EXPORT: 100.0,
            PipelineStep.COMPLETED: 100.0,
            PipelineStep.FAILED: self._last_progress,
        }
        return step_values.get(self.current_step, 0.0)

    @property
    def _last_progress(self) -> float:
        return 0.0


__all__ = ["PipelineState", "PipelineStep"]
