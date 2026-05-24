"""
Data types for InteractiveDataCollector — session and result objects.
"""

from __future__ import annotations

import time
import uuid
from typing import Any


class CompletionSession:
    """Python fallback session for template completion."""

    __slots__ = ("answers", "created_at", "niche_id", "round_count", "session_id")

    def __init__(self, niche_id: str) -> None:
        self.session_id = f"py-{niche_id}-{uuid.uuid4().hex[:8]}"
        self.niche_id = niche_id
        self.round_count = 0
        self.created_at = time.time()
        self.answers: dict[str, str] = {}


class InteractiveCollectionResult:
    """Result of an interactive data collection operation."""

    __slots__ = (
        "answers_applied",
        "answers_rejected",
        "completion_pct",
        "is_complete",
        "niche_id",
        "questions",
        "round_number",
        "session_id",
        "source",
        "still_missing",
    )

    def __init__(
        self,
        session_id: str = "",
        niche_id: str = "",
        questions: list[dict[str, Any]] | None = None,
        answers_applied: int = 0,
        answers_rejected: int = 0,
        still_missing: int = 0,
        completion_pct: float = 0.0,
        is_complete: bool = False,
        round_number: int = 0,
        source: str = "deterministic",
    ) -> None:
        self.session_id = session_id
        self.niche_id = niche_id
        self.questions = questions or []
        self.answers_applied = answers_applied
        self.answers_rejected = answers_rejected
        self.still_missing = still_missing
        self.completion_pct = completion_pct
        self.is_complete = is_complete
        self.round_number = round_number
        self.source = source


__all__ = ["CompletionSession", "InteractiveCollectionResult"]
