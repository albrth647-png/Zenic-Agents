"""Re-exports for engine package."""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from ._mixin_core import RiskPredictionEngine

_engine_instance: RiskPredictionEngine | None = None
_engine_lock = threading.Lock()


def get_risk_prediction_engine() -> RiskPredictionEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = RiskPredictionEngine()
        return _engine_instance


def reset_risk_prediction_engine() -> None:
    global _engine_instance
    with _engine_lock:
        _engine_instance = None


__all__ = [
    "RiskPredictionEngine",
    "get_risk_prediction_engine",
    "reset_risk_prediction_engine",
]
