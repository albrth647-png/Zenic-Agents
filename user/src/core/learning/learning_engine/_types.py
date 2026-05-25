"""Types and constants for learning_engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

DB_DIR = Path.home() / ".zenic_agents" / "db"

DB_PATH = DB_DIR / "learning.sqlite"


class LearningStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class LearningInsight:
    id: str = ""
    insight_type: str = ""
    pattern: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    supporting_outcomes: list[str] = field(default_factory=list)
    created_at: str = ""
    applied: bool = False


__all__ = ["DB_DIR", "DB_PATH", "LearningInsight", "LearningStrategy", "logger"]
