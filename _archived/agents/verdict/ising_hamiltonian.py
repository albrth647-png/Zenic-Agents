"""
Ising Hamiltonian para el motor TECE.

H = -∑ᵢ wᵢ · sᵢ - ∑ᵢⱼ Jᵢⱼ · sᵢ · sⱼ

Primer término: campo externo (peso individual de cada evidencia)
Segundo término: interacciones entre pares de evidencias (¡NUEVO!)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .interaction_matrix import InteractionMatrix
from .tece_types import (
    IsingConfig,
    SpinValue,
    ThermodynamicResult,
)

if TYPE_CHECKING:
    from ..schemas import Evidence


class IsingHamiltonian:
    """
    Calcula la energía de un sistema de evidencias usando el modelo de Ising.

    H = -∑ᵢ wᵢ · sᵢ - ∑ᵢⱼ Jᵢⱼ · sᵢ · sⱼ

    Donde:
    - wᵢ = evidence.weight × evidence_type_weight
    - sᵢ = +1 si favorece YES, -1 si favorece NO
    - Jᵢⱼ = interacción entre evidencia i y evidencia j
    """

    def __init__(
        self,
        config: IsingConfig | None = None,
        interactions: InteractionMatrix | None = None,
    ):
        self._config = config or IsingConfig()
        self._interactions = interactions or self._default_interactions()

    @staticmethod
    def _default_interactions() -> InteractionMatrix:
        """Crear matriz de interacciones con valores por defecto."""
        mat = InteractionMatrix()
        mat.init_defaults()
        return mat

    def compute_energy(
        self,
        evidence: list[Evidence],
        spins: list[SpinValue] | None = None,
    ) -> ThermodynamicResult:
        """
        Calcular la energía total del sistema.

        Args:
            evidence: Lista de evidencias
            spins: Estados de spin (+1/-1). Si es None, se infiere de evidence.favors

        Returns:
            ThermodynamicResult con todas las energías
        """
        if not evidence:
            return ThermodynamicResult(
                verdict="NO",
                confidence=0.0,
                ising_energy=0.0,
                source="tece_no_evidence",
            )

        # Inferir spins si no se proporcionan
        if spins is None:
            spins = [
                SpinValue.YES if e.favors == "YES" else SpinValue.NO
                for e in evidence
            ]

        # ── Verificar veto ──────────────────────────────────
        for e in evidence:
            if (
                e.evidence_type in self._config.veto_types
                and e.favors == "NO"
                and e.weight >= self._config.veto_threshold
            ):
                return ThermodynamicResult(
                    verdict="NO",
                    confidence=0.95,
                    ising_energy=-10.0,  # Energía muy negativa = NO sólido
                    field_energy=0.0,
                    interaction_energy=0.0,
                    temperature=1.0,
                    entropy=0.0,
                    free_energy=-10.0,
                    needs_llm=False,
                    source="tece_veto",
                    evidence_for=[e for e in evidence if e.favors == "YES"],
                    evidence_against=[e for e in evidence if e.favors == "NO"],
                )

        # ── Término 1: Campo externo (pesos individuales) ───
        # -∑ᵢ wᵢ · sᵢ
        field_energy = 0.0
        for i, e in enumerate(evidence):
            type_weight = self._config.evidence_weights.get(e.evidence_type, 1.0)
            w_i = e.weight * type_weight  # Peso efectivo
            s_i = float(spins[i])  # +1 o -1
            field_energy -= w_i * s_i

        # ── Término 2: Interacciones entre pares ────────────
        # -∑ᵢⱼ Jᵢⱼ · sᵢ · sⱼ
        interaction_energy = 0.0
        n = len(evidence)
        for i in range(n):
            for j in range(i + 1, n):
                J_ij = self._interactions.get(
                    evidence[i].evidence_type,
                    evidence[j].evidence_type,
                )
                if J_ij != 0.0:
                    interaction_energy -= J_ij * float(spins[i]) * float(spins[j])

        # ── Energía total ────────────────────────────────────
        ising_energy = field_energy + interaction_energy

        # ── Entropía (Shannon) ──────────────────────────────
        n_yes = sum(1 for e in evidence if e.favors == "YES")
        n_no = n - n_yes
        entropy = 0.0
        if n > 0:
            p_yes = n_yes / n
            p_no = n_no / n
            if p_yes > 0:
                entropy -= p_yes * math.log2(p_yes)
            if p_no > 0:
                entropy -= p_no * math.log2(p_no)

        # ── Free Energy (temperatura por defecto = 1.0) ─────
        temperature = 1.0
        free_energy = ising_energy - temperature * entropy

        # ── Determinar veredicto ────────────────────────────
        # Energía negativa → estado estable → YES
        # Energía positiva → estado inestable → NO
        # Entre más negativa, más seguro
        if ising_energy < -0.5:
            verdict = "YES"
            confidence = min(0.95, abs(ising_energy) / 10.0)
        elif ising_energy > 0.5:
            verdict = "NO"
            confidence = min(0.95, abs(ising_energy) / 10.0)
        else:
            # Zona de duda → necesita LLM o más evidencia
            verdict = "NO" if ising_energy >= 0 else "YES"
            confidence = 0.3
            needs_llm = True

        # Zona de duda
        needs_llm = abs(ising_energy) < 0.5

        # Construir explicación
        explanation = self._build_explanation(
            evidence, spins, field_energy, interaction_energy, ising_energy
        )

        return ThermodynamicResult(
            verdict=verdict,
            confidence=round(confidence, 2),
            ising_energy=round(ising_energy, 4),
            field_energy=round(field_energy, 4),
            interaction_energy=round(interaction_energy, 4),
            temperature=round(temperature, 2),
            entropy=round(entropy, 4),
            free_energy=round(free_energy, 4),
            needs_llm=needs_llm,
            source="tece_ising",
            evidence_for=[e for e in evidence if e.favors == "YES"],
            evidence_against=[e for e in evidence if e.favors == "NO"],
            explanation=explanation,
        )

    def compute_spin_energy(
        self, evidence: list[Evidence], spins: list[SpinValue]
    ) -> float:
        """
        Calcular energía para un estado de spin específico.

        Útil para el annealing: probar diferentes configuraciones de spin.
        Reusa compute_energy() internamente para evitar duplicación.
        """
        result = self.compute_energy(evidence, spins=spins)
        return result.ising_energy

    @property
    def interactions(self) -> InteractionMatrix:
        """Acceder a la matriz de interacciones."""
        return self._interactions

    def _build_explanation(
        self,
        evidence: list[Evidence],
        spins: list[SpinValue],
        field_energy: float,
        interaction_energy: float,
        total_energy: float,
    ) -> str:
        """Construir explicación legible del veredicto."""
        parts = []

        # Contribuciones individuales más fuertes
        strong_yes = []
        strong_no = []
        for i, e in enumerate(evidence):
            type_weight = self._config.evidence_weights.get(e.evidence_type, 1.0)
            contribution = e.weight * type_weight * float(spins[i])
            if e.favors == "YES" and contribution > 0.5:
                strong_yes.append(f"{e.evidence_type.value}(+{contribution:.1f})")
            elif e.favors == "NO" and abs(contribution) > 0.5:
                strong_no.append(f"{e.evidence_type.value}({contribution:.1f})")

        if strong_yes:
            parts.append(f"YES por: {', '.join(strong_yes)}")
        if strong_no:
            parts.append(f"NO por: {', '.join(strong_no)}")

        # Interacciones más fuertes
        strong_interactions = []
        n = len(evidence)
        for i in range(n):
            for j in range(i + 1, n):
                J = self._interactions.get(
                    evidence[i].evidence_type,
                    evidence[j].evidence_type,
                )
                if J != 0.0:
                    contrib = -J * float(spins[i]) * float(spins[j])
                    if abs(contrib) > 0.5:
                        pair = f"{evidence[i].evidence_type.value}+{evidence[j].evidence_type.value}"
                        strong_interactions.append(f"{pair}({contrib:+.1f})")

        if strong_interactions:
            parts.append(f"Interacciones: {', '.join(strong_interactions)}")

        # Resumen
        parts.append(f"Energía total: {total_energy:.2f} (H<0 = estable = favorable)")

        return " | ".join(parts)
