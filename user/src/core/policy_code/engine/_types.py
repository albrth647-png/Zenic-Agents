"""Types and constants for engine."""
from __future__ import annotations

from ..types import PolicyCondition

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("zenic_agents.core.policy_code.engine")

DB_DIR = Path.home() / ".zenic_agents" / "db"

DB_PATH = DB_DIR / "policy_code.sqlite"


class PolicyEvaluationResult:
    __slots__ = (
        "allowed",
        "conditions_failed",
        "conditions_met",
        "denied_by",
        "evaluation_time_ms",
        "matched_policies",
    )

    def __init__(
        self,
        allowed: bool = False,
        matched_policies: list[str] | None = None,
        denied_by: list[str] | None = None,
        conditions_met: list[str] | None = None,
        conditions_failed: list[str] | None = None,
        evaluation_time_ms: float = 0.0,
    ) -> None:
        self.allowed = allowed
        self.matched_policies = matched_policies or []
        self.denied_by = denied_by or []
        self.conditions_met = conditions_met or []
        self.conditions_failed = conditions_failed or []
        self.evaluation_time_ms = evaluation_time_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "matched_policies": self.matched_policies,
            "denied_by": self.denied_by,
            "conditions_met": self.conditions_met,
            "conditions_failed": self.conditions_failed,
            "evaluation_time_ms": round(self.evaluation_time_ms, 3),
        }


__all__ = ["DB_DIR", "DB_PATH", "PolicyCondition", "PolicyEvaluationResult", "logger"]
