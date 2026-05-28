from __future__ import annotations

try:
    from .outcome_tracker import (
        ActionOutcome,
        OutcomeStatus,
        OutcomeTracker,
        get_outcome_tracker,
        reset_outcome_tracker,
    )
except ImportError:
    OutcomeStatus = None  # type: ignore[misc,assignment]
    ActionOutcome = None  # type: ignore[misc,assignment]
    OutcomeTracker = None  # type: ignore[misc,assignment]
    get_outcome_tracker = None  # type: ignore[misc,assignment]
    reset_outcome_tracker = None  # type: ignore[misc,assignment]

try:
    from .learning_engine import (
        LearningEngine,
        LearningInsight,
        LearningStrategy,
        get_learning_engine,
        reset_learning_engine,
    )
except ImportError:
    LearningInsight = None  # type: ignore[misc,assignment]
    LearningStrategy = None  # type: ignore[misc,assignment]
    LearningEngine = None  # type: ignore[misc,assignment]
    get_learning_engine = None  # type: ignore[misc,assignment]
    reset_learning_engine = None  # type: ignore[misc,assignment]

__all__ = [
    "ActionOutcome",
    "LearningEngine",
    "LearningInsight",
    "LearningStrategy",
    "OutcomeStatus",
    "OutcomeTracker",
    "get_learning_engine",
    "get_outcome_tracker",
    "reset_learning_engine",
    "reset_outcome_tracker",
]
