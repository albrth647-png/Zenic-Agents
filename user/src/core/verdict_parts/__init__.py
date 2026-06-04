"""
Verdict Parts — Componentes del pipeline de veredicto.

Incluye:
  - DeterministicPipeline: 9 tareas determinísticas sin IA
  - EvidenceCollector: Recolección de evidencia
  - ConsensusResolver: Resolución de consenso
  - VerdictEngine: Motor de veredicto (solo SÍ/NO)

VORTEX 2.4: TopologicalRouter para redistribución causal
VORTEX 2.5: GeodesicTracker para mapeo de estados y rutas
VORTEX 2.7: verify_determinism() en cada componente
"""

from .consensus_resolver import ConsensusResolver
from .deterministic_pipeline import DeterministicPipeline
from .evidence_collector import EvidenceCollector
from .types import (
    ConsensusResult,
    DeterministicResult,
    Evidence,
    EvidenceType,
    Verdict,
    VerdictConfidence,
    VerdictInput,
    VerdictOutput,
)

__all__ = [
    "ConsensusResolver",
    "ConsensusResult",
    "DeterministicPipeline",
    "DeterministicResult",
    "Evidence",
    "EvidenceCollector",
    "EvidenceType",
    "Verdict",
    "VerdictConfidence",
    "VerdictInput",
    "VerdictOutput",
    "VerdictEngine",
]


def __getattr__(name):
    """Lazy import of VerdictEngine to avoid circular import with verdict_engine_module."""
    if name == "VerdictEngine":
        from .verdict_engine import VerdictEngine
        return VerdictEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
