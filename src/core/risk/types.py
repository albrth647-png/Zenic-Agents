from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BlastRadiusReport:
    source_node: str
    affected_nodes: list[str] = field(default_factory=list)
    direct_dependents: list[str] = field(default_factory=list)
    transitive_dependents: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.NEGLIGIBLE
    blast_radius_size: int = 0
    recommendations: list[str] = field(default_factory=list)


@dataclass
class RiskPropagationReport:
    effective_risks: dict[str, float] = field(default_factory=dict)
    max_effective_risk: float = 0.0
    high_risk_nodes: list[str] = field(default_factory=list)
    risk_paths: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CriticalPathReport:
    critical_path: list[str] = field(default_factory=list)
    total_duration_ms: int = 0
    is_on_critical_path: dict[str, bool] = field(default_factory=dict)


@dataclass
class CompositeRiskReport:
    blast_radius: BlastRadiusReport = field(default_factory=BlastRadiusReport)
    propagation: RiskPropagationReport = field(default_factory=RiskPropagationReport)
    critical_path: CriticalPathReport = field(default_factory=CriticalPathReport)
    overall_risk_score: float = 0.0
    summary: str = ""
