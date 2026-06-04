"""
ZENIC-AGENTS — Collector Routes (InteractiveDataCollector).

REST endpoints for interactive data collection sessions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_collector
from ..middleware import check_collector_limit, get_current_tenant
from ..schemas import (
    CollectorAnswerRequest,
    CollectorBatchAnswerRequest,
    CollectorFinalizeRequest,
    CollectorQuestionsRequest,
    CollectorSessionResponse,
    CollectorStartRequest,
    CollectorSuggestionsRequest,
    CollectorValidateRequest,
)

router = APIRouter(prefix="/collector", tags=["collector"])


@router.post("/start", response_model=CollectorSessionResponse)
def start_session(
    payload: CollectorStartRequest,
    tenant: dict = Depends(check_collector_limit),
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Start a new interactive collection session (plan limit enforced)."""
    result = collector.execute({
        "action": "start",
        "niche_id": payload.niche_id,
    })

    # Record usage
    from ..plans import get_plan_manager
    get_plan_manager().record_collector_session(tenant["id"])

    return _to_response(result)


@router.post("/questions", response_model=CollectorSessionResponse)
def get_questions(
    payload: CollectorQuestionsRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Get the next batch of questions for a session."""
    result = collector.execute({
        "action": "get_questions",
        "session_id": payload.session_id,
        "template_dict": payload.template_dict,
    })
    return _to_response(result)


@router.post("/answer", response_model=CollectorSessionResponse)
def submit_answer(
    payload: CollectorAnswerRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Submit a single answer to a question."""
    result = collector.execute({
        "action": "submit_answer",
        "session_id": payload.session_id,
        "template_dict": payload.template_dict,
        "field_name": payload.field_name,
        "value": payload.value,
        "field_type": payload.field_type,
    })
    return _to_response(result)


@router.post("/answers", response_model=CollectorSessionResponse)
def submit_answers(
    payload: CollectorBatchAnswerRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Submit multiple answers at once."""
    result = collector.execute({
        "action": "submit_answers",
        "session_id": payload.session_id,
        "template_dict": payload.template_dict,
        "answers": payload.answers,
    })
    return _to_response(result)


@router.post("/validate", response_model=CollectorSessionResponse)
def validate_answer(
    payload: CollectorValidateRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Validate an answer without submitting it."""
    result = collector.execute({
        "action": "validate",
        "field_type": payload.field_type,
        "value": payload.value,
        "enum_variants": payload.enum_variants,
    })
    return _to_response(result)


@router.get("/{session_id}/progress", response_model=CollectorSessionResponse)
def get_progress(
    session_id: str,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Get the current progress of a session."""
    result = collector.execute({
        "action": "progress",
        "session_id": session_id,
    })
    return _to_response(result)


@router.post("/finalize", response_model=CollectorSessionResponse)
def finalize_session(
    payload: CollectorFinalizeRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Finalize a session and get the completed template."""
    result = collector.execute({
        "action": "finalize",
        "session_id": payload.session_id,
        "template_dict": payload.template_dict,
    })
    return _to_response(result)


@router.post("/suggestions", response_model=CollectorSessionResponse)
def get_suggestions(
    payload: CollectorSuggestionsRequest,
    collector=Depends(get_collector),
) -> CollectorSessionResponse:
    """Get suggestions for a field."""
    result = collector.execute({
        "action": "suggestions",
        "field_name": payload.field_name,
        "field_type": payload.field_type,
    })
    return _to_response(result)


# ── Helper ────────────────────────────────────────────────────

def _to_response(result) -> CollectorSessionResponse:
    """Convert an InteractiveCollectionResult to the API response model."""
    if hasattr(result, "__dict__"):
        d = {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
    elif isinstance(result, dict):
        d = result
    else:
        d = {}
    return CollectorSessionResponse(
        session_id=d.get("session_id", ""),
        niche_id=d.get("niche_id", ""),
        questions=d.get("questions", []),
        answers_applied=d.get("answers_applied", 0),
        answers_rejected=d.get("answers_rejected", 0),
        still_missing=d.get("still_missing", 0),
        completion_pct=d.get("completion_pct", 0.0),
        is_complete=d.get("is_complete", False),
        round_number=d.get("round_number", 0),
        source=d.get("source", "deterministic"),
    )
