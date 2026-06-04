"""
Thermodynamic Entropy Consensus Engine (TECE) — Tipos de datos.

Fase 1: Ising Hamiltonian
Fase 2: Free Energy
Fase 3: Thermodynamic Annealing
Fase 4: Kolmogorov Audit

Ising Hamiltonian base:
    H = -∑ᵢ wᵢ·sᵢ - ∑ᵢⱼ Jᵢⱼ·sᵢ·sⱼ

Free Energy (Helmholtz):
    F = H - T·S

Donde:
    sᵢ ∈ {+1, -1}  → spin de cada evidencia
    wᵢ              → peso base (evidence.weight × type_weight)
    Jᵢⱼ              → interacción entre evidencias i y j
    T               → temperatura dinámica
    S               → entropía de Shannon
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from ..schemas import Evidence, EvidenceType


class SpinValue(IntEnum):
    """Estado de spin de una evidencia — +1 = YES, -1 = NO."""

    YES = 1
    NO = -1


@dataclass
class InteractionConfig:
    """
    Configuración de la matriz de interacciones Jᵢⱼ.

    J[i][j] > 0 → las evidencias i y j se refuerzan mutuamente
    J[i][j] < 0 → las evidencias i y j se contradicen
    J[i][j] = 0 → las evidencias i y j son independientes
    """

    # Interacciones por defecto entre pares de EvidenceType
    # Formato: {(type_a, type_b): valor}
    defaults: dict[tuple[EvidenceType, EvidenceType], float] = field(default_factory=dict)

    # Factor de escala global para todas las interacciones
    # Si es 0, el sistema se comporta como el ConsensusResolver original
    scale: float = 1.0


@dataclass
class SpinState:
    """
    Estado de un conjunto de evidencias como spins de Ising.

    Cada evidencia se mapea a un spin: YES→+1, NO→-1.
    """

    # Mapeo de índice de evidencia → SpinValue
    spins: list[SpinValue] = field(default_factory=list)

    # Evidencias originales (para trazabilidad)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def energy(self) -> float:
        """Energía actual del estado (se actualiza externamente)."""
        return 0.0

    @property
    def magnetization(self) -> float:
        """Magnetización: promedio de spins. +1 = todos YES, -1 = todos NO."""
        if not self.spins:
            return 0.0
        return sum(self.spins) / len(self.spins)


@dataclass
class IsingConfig:
    """
    Configuración del modelo de Ising para el consenso.

    H = -∑ᵢ wᵢ·sᵢ - ∑ᵢⱼ Jᵢⱼ·sᵢ·sⱼ
    """

    # Pesos base por tipo de evidencia (mismos que ConsensusResolver actual)
    evidence_weights: dict[EvidenceType, float] = field(default_factory=lambda: {
        EvidenceType.SECURITY_CHECK: 1.5,
        EvidenceType.SANDBOX_PASS: 1.5,
        EvidenceType.SYNTAX_VALID: 1.2,
        EvidenceType.AST_VALIDATION: 1.2,
        EvidenceType.CACHE_HIT: 1.3,
        EvidenceType.TYPE_SAFETY: 1.1,
        EvidenceType.RULE_ENGINE: 1.0,
        EvidenceType.PATTERN_MATCH: 0.8,
        EvidenceType.STRUCTURAL_MATCH: 0.7,
        EvidenceType.REGEX_MATCH: 0.6,
        EvidenceType.KEYWORD_CLASSIFY: 0.5,
        EvidenceType.SEMANTIC_SIMILARITY: 0.4,
    })

    # Tipos de veto (interrumpen el cálculo con NO inmediato)
    veto_types: set[EvidenceType] = field(default_factory=lambda: {
        EvidenceType.SECURITY_CHECK,
        EvidenceType.SANDBOX_PASS,
    })

    # Threshold de veto
    veto_threshold: float = 0.7


@dataclass
class ThermodynamicResult:
    """
    Resultado completo del motor termodinámico.

    Incluye no solo el veredicto, sino toda la física detrás.
    """

    # Veredicto final (string para compatibilidad con ising_hamiltonian)
    verdict: str = "NO"
    confidence: float = 0.0

    # Energías
    ising_energy: float = 0.0          # H
    field_energy: float = 0.0          # -∑ wᵢ·sᵢ
    interaction_energy: float = 0.0    # -∑ Jᵢⱼ·sᵢ·sⱼ

    # Termodinámica
    temperature: float = 1.0           # T
    entropy: float = 0.0               # S
    free_energy: float = 0.0           # F = H - T·S

    # Kolmogorov audit
    kolmogorov_complexity: float = 0.0
    kolmogorov_passed: bool = True

    # Annealing
    annealing_iterations: int = 0
    annealing_converged: bool = True

    # Metadata
    needs_llm: bool = False
    source: str = "tece_deterministic"
    evidence_for: list[Evidence] = field(default_factory=list)
    evidence_against: list[Evidence] = field(default_factory=list)

    # Explicación causal
    explanation: str = ""


@dataclass
class AnnealingConfig:
    """Configuración del recocido simulado termodinámico."""

    # Temperatura inicial y final
    temperature_initial: float = 1.0
    temperature_final: float = 0.01

    # Factor de enfriamiento
    cooling_rate: float = 0.95

    # Máximo de iteraciones
    max_iterations: int = 1000

    # Recalentamiento: si no mejora en N pasos, T *= 1.5
    stuck_threshold: int = 20
    reheat_factor: float = 1.5

    # Límite de recalientamientos
    max_reheats: int = 3


@dataclass
class AnnealingResult:
    """Resultado del proceso de recocido."""

    # Estado final
    final_spins: list[SpinValue] = field(default_factory=list)
    final_energy: float = 0.0

    # Mejor estado encontrado
    best_spins: list[SpinValue] = field(default_factory=list)
    best_energy: float = 0.0

    # Estadísticas
    iterations: int = 0
    reheats: int = 0
    converged: bool = True

    # Traza de energía (para depuración)
    energy_trace: list[float] = field(default_factory=list)


@dataclass
class TemperatureHistory:
    """Historial de temperatura para el controlador dinámico."""

    total_decisions: int = 0
    correct_decisions: int = 0
    temperature: float = 1.0
    base_temperature: float = 1.0
    recent_accuracy: list[float] = field(default_factory=list)
    window_size: int = 100
