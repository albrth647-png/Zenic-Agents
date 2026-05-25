"""
ZENIC-AGENTS - Safety Gate for Executors (Phase 3 + Phase D)

Pre-execution validation layer that enforces deterministic safety rules
BEFORE any executor runs. Safety Gate veto is ABSOLUTE — no override possible.

Phase D extensions:
    - DomainSafetyGate: domain-specific rules + compliance validation
    - ComplianceResult: compliance check result
    - DomainSafetyCheckResult: extended safety check result with domain info
"""

from ._gate import ActionRateLimiter, SafetyGate, get_default_safety_gate, reset_safety_gate, set_default_safety_gate
from ._types import SAFETY_RULES, ActionCategory, SafetyCheckResult, SafetyRule, SafetyVerdict
from .domain_gate import (
    ComplianceResult,
    DomainSafetyCheckResult,
    DomainSafetyGate,
    get_default_domain_safety_gate,
)

__all__ = [
    "SAFETY_RULES",
    "ActionCategory",
    "ActionRateLimiter",
    "ComplianceResult",
    "DomainSafetyCheckResult",
    "DomainSafetyGate",
    "SafetyCheckResult",
    "SafetyGate",
    "SafetyRule",
    "SafetyVerdict",
    "get_default_domain_safety_gate",
    "get_default_safety_gate",
    "reset_safety_gate",
    "set_default_safety_gate",
]
