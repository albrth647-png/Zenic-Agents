"""Re-exports for engine package."""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["Any", "Dict", "List", "Tuple", "logging"]

_engine_instance: RiskPredictionEngine | None = None  # noqa: F821  # TODO: verify import
_engine_lock = threading.Lock()


def get_risk_prediction_engine() -> RiskPredictionEngine:  # noqa: F821  # TODO: verify import
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = RiskPredictionEngine()  # noqa: F821  # TODO: Phase3 - verify import
        return _engine_instance


def reset_risk_prediction_engine() -> None:
    global _engine_instance
    with _engine_lock:
        _engine_instance = None
