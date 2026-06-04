"""
TECE ConsensusResolver — Reemplazo determinista del ConsensusResolverV18.

Fases implementadas:
  ✅ Fase 1: Ising Hamiltonian (H = -∑wᵢsᵢ - ∑Jᵢⱼsᵢsⱼ)
  ✅ Fase 2: Free Energy (F = H - T·S) con temperatura dinámica
  ❌ Fase 3: Thermodynamic Annealing — en construcción
  ❌ Fase 4: Kolmogorov Audit — en construcción

Output compatible con VerdictEngineV18 (produce ConsensusResult).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..resilience import BaseAgent
from ..schemas import ConsensusResult, Evidence, Verdict
from .free_energy import FreeEnergyMinimizer
from .ising_hamiltonian import IsingHamiltonian
from .temperature_controller import TemperatureController

if TYPE_CHECKING:
    from .interaction_matrix import InteractionMatrix
    from .tece_types import IsingConfig, ThermodynamicResult


class IsingConsensusResolver(BaseAgent[ConsensusResult]):
    """
    TECE ConsensusResolver — Reemplaza ConsensusResolverV18.

    Usa Free Energy (F = H - T·S) en lugar de suma lineal de pesos:
      - H: Ising energy con interacciones Jᵢⱼ entre evidencias
      - T: Temperatura dinámica (se adapta al historial de aciertos)
      - S: Entropía de Shannon (mide división entre evidencias)

    Ventajas:
    - Captura sinergias entre evidencias (Jᵢⱼ)
    - Temperatura adaptativa (sube tras fallos, baja tras aciertos)
    - Explicaciones causales con física estadística
    - Misma interfaz que ConsensusResolverV18
    """

    def __init__(
        self,
        config: IsingConfig | None = None,
        interactions: InteractionMatrix | None = None,
        temperature_controller: TemperatureController | None = None,
        **kwargs,
    ) -> None:
        super().__init__(name="A42_TECE_ConsensusResolver", **kwargs)
        self._hamiltonian = IsingHamiltonian(config=config, interactions=interactions)
        self._temperature = temperature_controller or TemperatureController()
        self._free_energy = FreeEnergyMinimizer(
            hamiltonian=self._hamiltonian,
            temperature_controller=self._temperature,
            config=config,
        )

    def execute(self, input_data: Any) -> ConsensusResult:
        """Resolver consenso usando Free Energy (F = H - T·S).

        input_data: list[Evidence] o dict con clave 'evidence'.
        """
        evidence: list[Evidence] = []

        if isinstance(input_data, list):
            evidence = input_data
        elif isinstance(input_data, dict):
            evidence = input_data.get("evidence", [])

        if not evidence:
            return ConsensusResult(
                verdict=Verdict.NO,
                confidence=0.0,
                needs_llm=True,
                source="tece_no_evidence",
            )

        # Calcular Free Energy del sistema
        result: ThermodynamicResult = self._free_energy.compute(evidence)

        # Convertir a ConsensusResult (compatible con VerdictEngineV18)
        return ConsensusResult(
            verdict=Verdict.YES if result.verdict == "YES" else Verdict.NO,
            confidence=result.confidence,
            score=round(-result.free_energy / 10.0, 3),  # Normalizado a [-1,1]
            evidence_for=result.evidence_for,
            evidence_against=result.evidence_against,
            needs_llm=result.needs_llm,
            signals_count=len(evidence),
            unanimous=(
                all(e.favors == evidence[0].favors for e in evidence)
                if evidence
                else False
            ),
            source=result.source,
        )

    def record_outcome(self, was_correct: bool) -> None:
        """Registrar si la decisión fue correcta (para ajustar temperatura)."""
        self._temperature.record_outcome(was_correct)

    def fallback(self, input_data: Any) -> ConsensusResult:
        """Fallback: NO por precaución."""
        return ConsensusResult(
            verdict=Verdict.NO,
            confidence=0.1,
            needs_llm=False,
            source="tece_fallback",
        )

    @property
    def hamiltonian(self) -> IsingHamiltonian:
        return self._hamiltonian

    @property
    def temperature_controller(self) -> TemperatureController:
        return self._temperature

    @property
    def free_energy_minimizer(self) -> FreeEnergyMinimizer:
        return self._free_energy
