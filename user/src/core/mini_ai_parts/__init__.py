"""
MiniAIEngine sub-package — Qwen3-0.6B verdict-only engine (v17.1).

Motor de VEREDICTO - La IA solo dice SÍ o NO.

v17.1: Las 7 tareas bounded son 100% determinísticas.
       Solo verdict() usa el LLM, con resiliencia completa.
"""

from ._engine import MiniAIEngine
from ._fallbacks import FallbackMethodsMixin
from ._imports import (
    LLM_TIMEOUT_S,
    MAX_TOKENS_CLASSIFY,
    MAX_TOKENS_EXPLAIN,
    MAX_TOKENS_EXTRACT,
    MAX_TOKENS_GENERATE,
    MAX_TOKENS_PATTERN,
    MAX_TOKENS_SUBTASK,
    MAX_TOKENS_TEMPLATE,
    MODEL_DIR,
    MODEL_FILENAME,
    MODEL_PATH,
    N_CTX,
    N_THREADS,
    TEMPERATURE,
    IntentResult,
)
from ._lifecycle import ModelLifecycleMixin
from ._tasks import BoundedTasksMixin

__all__ = [
    "LLM_TIMEOUT_S",
    "MAX_TOKENS_CLASSIFY",
    "MAX_TOKENS_EXPLAIN",
    "MAX_TOKENS_EXTRACT",
    "MAX_TOKENS_GENERATE",
    "MAX_TOKENS_PATTERN",
    "MAX_TOKENS_SUBTASK",
    "MAX_TOKENS_TEMPLATE",
    "MODEL_DIR",
    "MODEL_FILENAME",
    "MODEL_PATH",
    "N_CTX",
    "N_THREADS",
    "TEMPERATURE",
    "BoundedTasksMixin",
    "FallbackMethodsMixin",
    "IntentResult",
    "MiniAIEngine",
    "ModelLifecycleMixin",
]
