"""
Free Energy Minimizer — Integra temperatura dinámica + entropía al Ising Hamiltonian.

F = H - T · S

Donde:
  H = Ising energy (-∑wᵢsᵢ - ∑Jᵢⱼsᵢsⱼ)
  T = Temperatura dinámica (desde TemperatureController)
  S = Entropía de Shannon (desde EntropyCalculator)

Cuando T es alta → el sistema es más conservador (penaliza la duda)
Cuando T es baja → el sistema es más seguro (confía en la energía)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .entropy_calculator import EntropyCalculator
from .ising_hamiltonian import IsingHamiltonian
from .tece_types import IsingConfig, ThermodynamicResult
from .temperature_controller import TemperatureController

if TYPE_CHECKING:
    from ..schemas import Evidence


class FreeEnergyMinimizer:
    """
    Calcula la Free Energy de Helmholtz para un sistema de evidencias.

    F = H - T · S

    La minimización de F encuentra el equilibrio entre:
    - Baja energía H (evidencia fuerte → decisión clara)
    - Baja entropía S (evidencias unánimes → certeza)
    - Temperatura T adaptativa (historial de aciertos/fallos)
    """

    def __init__(
        self,
        hamiltonian: IsingHamiltonian | None = None,
        temperature_controller: TemperatureController | None = None,
        config: IsingConfig | None = None,
    ):
        self._hamiltonian = hamiltonian or IsingHamiltonian(config=config)
        self._temperature = temperature_controller or TemperatureController()

    def compute(
        self,
        evidence: list[Evidence],
    ) -> ThermodynamicResult:
        """
        Calcular la Free Energy del sistema.

        Args:
            evidence: Lista de evidencias

        Returns:
            ThermodynamicResult con F, H, T, S
        """
        # 1. Obtener energía base del Hamiltoniano de Ising
        base_result = self._hamiltonian.compute_energy(evidence)

        # 2. Obtener temperatura actual
        temperature = self._temperature.get_temperature()

        # 3. Calcular entropía desde las evidencias
        n_yes = sum(1 for e in evidence if e.favors == "YES")
        n_no = len(evidence) - n_yes
        entropy = EntropyCalculator.compute(n_yes, n_no)

        # 4. Free Energy: F = H - T · S
        # Si T es alta → el término T·S pesa más → F sube → más difícil decir YES
        # Si T es baja → el término T·S pesa menos → F se acerca a H
        free_energy = base_result.ising_energy - temperature * entropy

        # 5. Ajustar veredicto basado en Free Energy
        verdict = base_result.verdict
        confidence = base_result.confidence
        needs_llm = base_result.needs_llm

        # La Free Energy modifica la confianza
        # Si F es muy negativa → muy estable → alta confianza
        # Si F es cercana a 0 → inestable → duda
        if free_energy < -1.0:
            confidence = min(0.98, abs(free_energy) / 5.0)
            needs_llm = False
        elif free_energy > 0.5:
            # Free Energy positiva = sistema inestable = NO
            verdict = "NO"
            confidence = 0.2
            needs_llm = True
        else:
            # Zona de transición: -1.0 < F < 0.5
            confidence = max(0.1, abs(free_energy))
            needs_llm = True

        # 6. Construir resultado completo
        explanation = (
            f"{base_result.explanation} | "
            f"Free Energy: F={free_energy:.3f} = H({base_result.ising_energy:.3f}) "
            f"- T({temperature:.2f})·S({entropy:.3f})"
        )

        result = ThermodynamicResult(
            verdict=verdict,
            confidence=round(confidence, 2),
            ising_energy=base_result.ising_energy,
            field_energy=base_result.field_energy,
            interaction_energy=base_result.interaction_energy,
            temperature=round(temperature, 2),
            entropy=round(entropy, 4),
            free_energy=round(free_energy, 4),
            needs_llm=needs_llm,
            source="tece_free_energy",
            evidence_for=[e for e in evidence if e.favors == "YES"],
            evidence_against=[e for e in evidence if e.favors == "NO"],
            explanation=explanation,
        )

        return result

    @property
    def temperature_controller(self) -> TemperatureController:
        return self._temperature

    @property
    def hamiltonian(self) -> IsingHamiltonian:
        return self._hamiltonian
