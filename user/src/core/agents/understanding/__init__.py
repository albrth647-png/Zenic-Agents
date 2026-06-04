"""Layer 1: Understanding agents — ARCHIVED.
All understanding agents were unused (zero external references).
Shared intent utilities preserved for backward compatibility.
"""

# Shared intent utilities — migrated from agents/intent_shared.py
from .intent_utils import (
    GOAL_KEYWORDS,
    OP_KEYWORDS,
    VALID_GOALS,
    VALID_OPERATIONS,
    extract_code_block,
    extract_entities,
    extract_target_and_language,
    infer_criticality,
    infer_template_type,
)

__all__ = [
    "GOAL_KEYWORDS",
    "OP_KEYWORDS",
    "VALID_GOALS",
    "VALID_OPERATIONS",
    # Shared intent utilities
    "extract_code_block",
    "extract_entities",
    "extract_target_and_language",
    "infer_criticality",
    "infer_template_type",
]
