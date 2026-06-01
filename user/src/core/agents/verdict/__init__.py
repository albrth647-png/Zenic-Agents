"""
Layer 8: Verdict Engine — the ONLY place where AI is used.

TECE (Thermodynamic Entropy Consensus Engine):
  Fase 1: Ising Hamiltonian — interacciones entre evidencias (Jᵢⱼ)
  Fase 2: Free Energy — temperatura dinámica + entropía
  Fase 3: Thermodynamic Annealing — optimización global
  Fase 4: Kolmogorov Audit — filtro de auditabilidad
"""

from .consensus_resolver import ConsensusResolverV18
from .deterministic_pipeline import DeterministicPipeline
from .evidence_collector import EvidenceCollectorV18
from .interaction_matrix import InteractionMatrix
from .ising_consensus_resolver import IsingConsensusResolver
from .ising_hamiltonian import IsingHamiltonian
from .tece_types import (
    AnnealingConfig,
    AnnealingResult,
    InteractionConfig,
    IsingConfig,
    SpinState,
    SpinValue,
    TemperatureHistory,
    ThermodynamicResult,
)
from .verdict_engine import VerdictEngineV18

__all__ = [
    "AnnealingConfig",
    "AnnealingResult",
    "ConsensusResolverV18",
    "DeterministicPipeline",
    "EvidenceCollectorV18",
    "InteractionConfig",
    "InteractionMatrix",
    "IsingConfig",
    "IsingConsensusResolver",
    "IsingHamiltonian",
    "SpinState",
    "SpinValue",
    "TemperatureHistory",
    "ThermodynamicResult",
    "VerdictEngineV18",
]
