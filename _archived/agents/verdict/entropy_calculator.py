"""
EntropyCalculator — Entropía de Shannon sobre distribución de evidencias.

S = -∑ p(s) · log₂(p(s))

Usada por la Free Energy: F = H - T·S

Alta entropía = evidencias divididas (poca certeza)
Baja entropía = evidencias unánimes (mucha certeza)
"""

from __future__ import annotations

import math


class EntropyCalculator:
    """
    Calcula la entropía de Shannon de una distribución de evidencias.

    Útil para medir qué tan divididas están las evidencias:
    - S ≈ 0.0 → todas las evidencias apuntan al mismo lado (certeza)
    - S ≈ 1.0 → evidencias perfectamente divididas (máxima duda)
    """

    @staticmethod
    def compute(n_yes: int, n_no: int) -> float:
        """
        Calcular entropía de una distribución binaria.

        Args:
            n_yes: Número de evidencias que favorecen YES
            n_no: Número de evidencias que favorecen NO

        Returns:
            Entropía en bits [0.0, 1.0]
        """
        total = n_yes + n_no
        if total == 0:
            return 0.0

        p_yes = n_yes / total
        p_no = n_no / total

        entropy = 0.0
        if p_yes > 0:
            entropy -= p_yes * math.log2(p_yes)
        if p_no > 0:
            entropy -= p_no * math.log2(p_no)

        return entropy

    @staticmethod
    def normalized_entropy(n_yes: int, n_no: int) -> float:
        """
        Entropía normalizada a [0, 1].

        0.0 = todas las evidencias iguales (unánime)
        1.0 = evidencias perfectamente divididas (máxima duda)
        """
        entropy = EntropyCalculator.compute(n_yes, n_no)
        # La entropía máxima para binario es 1.0 bit
        return min(1.0, entropy)

    @staticmethod
    def confidence_from_entropy(entropy: float) -> float:
        """
        Convertir entropía a confianza.

        Confianza = 1.0 - entropía normalizada

        Args:
            entropy: Entropía de Shannon

        Returns:
            Confianza en [0, 1]
        """
        return 1.0 - min(1.0, entropy)

    @staticmethod
    def is_decisive(entropy: float, threshold: float = 0.3) -> bool:
        """
        Determinar si la entropía es lo suficientemente baja para decidir.

        Args:
            entropy: Entropía de Shannon
            threshold: Umbral por debajo del cual se considera decisivo

        Returns:
            True si la entropía está por debajo del umbral
        """
        return entropy <= threshold
