"""
InteractionMatrix Jᵢⱼ — Interacciones entre pares de EvidenceType.

Modelo de Ising:
    H_interaction = -∑ᵢⱼ Jᵢⱼ · sᵢ · sⱼ

J[i][j] > 0 → las evidencias se refuerzan mutuamente
J[i][j] < 0 → las evidencias se contradicen
J[i][j] = 0 → las evidencias son independientes

La matriz es simétrica: J[i][j] == J[j][i]
"""

from __future__ import annotations

from collections import defaultdict

from ..schemas import EvidenceType

# ──────────────────────────────────────────────────────────────
#  INTERACCIONES POR DEFECTO
# ──────────────────────────────────────────────────────────────
# Basadas en: ¿estas dos evidencias juntas dan más señal que separadas?
#
# Escala: 0.0 (independientes) a 2.0 (máxima sinergia)
# Negativo: se contradicen

_DEFAULT_INTERACTIONS: dict[tuple[EvidenceType, EvidenceType], float] = {
    # ── Seguridad + todo lo demás ──────────────────────────
    # Security + Critical = MUY fuerte (si algo es crítico Y peligroso, es NO)
    (EvidenceType.SECURITY_CHECK, EvidenceType.CRITICALITY): 2.0,
    # Security + Sandbox = fuerte (ambas son de seguridad)
    (EvidenceType.SECURITY_CHECK, EvidenceType.SANDBOX_PASS): 1.8,
    # Security + Syntax = irrelevante (no interactúan)
    (EvidenceType.SECURITY_CHECK, EvidenceType.SYNTAX_VALID): 0.0,
    # Security + Type = irrelevante
    (EvidenceType.SECURITY_CHECK, EvidenceType.TYPE_SAFETY): 0.0,
    # Security + Cache = irrelevante
    (EvidenceType.SECURITY_CHECK, EvidenceType.CACHE_HIT): 0.0,
    # Security + AST = débil (AST puede revelar patrones peligrosos)
    (EvidenceType.SECURITY_CHECK, EvidenceType.AST_VALIDATION): 0.5,
    # Security + Pattern = medio
    (EvidenceType.SECURITY_CHECK, EvidenceType.PATTERN_MATCH): 0.4,
    # Security + Structural = medio
    (EvidenceType.SECURITY_CHECK, EvidenceType.STRUCTURAL_MATCH): 0.3,
    # Security + Regex = débil
    (EvidenceType.SECURITY_CHECK, EvidenceType.REGEX_MATCH): 0.2,
    # Security + Keyword = medio
    (EvidenceType.SECURITY_CHECK, EvidenceType.KEYWORD_CLASSIFY): 0.5,
    # Security + Semantic = débil
    (EvidenceType.SECURITY_CHECK, EvidenceType.SEMANTIC_SIMILARITY): 0.3,
    # Security + Rule = fuerte
    (EvidenceType.SECURITY_CHECK, EvidenceType.RULE_ENGINE): 1.0,

    # ── Criticality + otros ────────────────────────────────
    (EvidenceType.CRITICALITY, EvidenceType.SANDBOX_PASS): 1.5,
    (EvidenceType.CRITICALITY, EvidenceType.INTENT_CLASSIFY): 1.5,
    (EvidenceType.CRITICALITY, EvidenceType.SYNTAX_VALID): 0.0,
    (EvidenceType.CRITICALITY, EvidenceType.TYPE_SAFETY): 0.2,
    (EvidenceType.CRITICALITY, EvidenceType.CACHE_HIT): 0.0,
    (EvidenceType.CRITICALITY, EvidenceType.AST_VALIDATION): 0.5,
    (EvidenceType.CRITICALITY, EvidenceType.PATTERN_MATCH): 0.3,
    (EvidenceType.CRITICALITY, EvidenceType.KEYWORD_CLASSIFY): 0.8,
    (EvidenceType.CRITICALITY, EvidenceType.SEMANTIC_SIMILARITY): 0.2,
    (EvidenceType.CRITICALITY, EvidenceType.RULE_ENGINE): 1.2,

    # ── Sandbox + otros ────────────────────────────────────
    (EvidenceType.SANDBOX_PASS, EvidenceType.SYNTAX_VALID): 0.0,
    (EvidenceType.SANDBOX_PASS, EvidenceType.TYPE_SAFETY): 0.0,
    (EvidenceType.SANDBOX_PASS, EvidenceType.CACHE_HIT): 0.0,
    (EvidenceType.SANDBOX_PASS, EvidenceType.AST_VALIDATION): 0.3,
    (EvidenceType.SANDBOX_PASS, EvidenceType.KEYWORD_CLASSIFY): 0.3,
    (EvidenceType.SANDBOX_PASS, EvidenceType.RULE_ENGINE): 0.8,

    # ── Intent classify + otros ────────────────────────────
    (EvidenceType.INTENT_CLASSIFY, EvidenceType.SYNTAX_VALID): 0.0,
    (EvidenceType.INTENT_CLASSIFY, EvidenceType.TYPE_SAFETY): 0.0,
    (EvidenceType.INTENT_CLASSIFY, EvidenceType.CACHE_HIT): 0.0,
    (EvidenceType.INTENT_CLASSIFY, EvidenceType.KEYWORD_CLASSIFY): 1.0,
    (EvidenceType.INTENT_CLASSIFY, EvidenceType.SEMANTIC_SIMILARITY): 0.6,

    # ── Sintaxis + otros ───────────────────────────────────
    (EvidenceType.SYNTAX_VALID, EvidenceType.TYPE_SAFETY): 1.0,
    (EvidenceType.SYNTAX_VALID, EvidenceType.AST_VALIDATION): 1.5,
    (EvidenceType.SYNTAX_VALID, EvidenceType.PATTERN_MATCH): 0.0,
    (EvidenceType.SYNTAX_VALID, EvidenceType.CACHE_HIT): 0.3,

    # ── Keyword + Semantic → se contradicen ────────────────
    (EvidenceType.KEYWORD_CLASSIFY, EvidenceType.SEMANTIC_SIMILARITY): -1.0,
    (EvidenceType.KEYWORD_CLASSIFY, EvidenceType.REGEX_MATCH): 0.7,
    (EvidenceType.KEYWORD_CLASSIFY, EvidenceType.PATTERN_MATCH): 0.6,
    (EvidenceType.KEYWORD_CLASSIFY, EvidenceType.RULE_ENGINE): 0.5,

    # ── Pattern + Structural ───────────────────────────────
    (EvidenceType.PATTERN_MATCH, EvidenceType.STRUCTURAL_MATCH): 1.2,
    (EvidenceType.PATTERN_MATCH, EvidenceType.REGEX_MATCH): 0.5,
    (EvidenceType.PATTERN_MATCH, EvidenceType.RULE_ENGINE): 0.4,

    # ── AST + Type ─────────────────────────────────────────
    (EvidenceType.AST_VALIDATION, EvidenceType.TYPE_SAFETY): 1.0,

    # ── Rule Engine + otros ────────────────────────────────
    (EvidenceType.RULE_ENGINE, EvidenceType.SEMANTIC_SIMILARITY): 0.0,

    # ── Cache + otros ──────────────────────────────────────
    (EvidenceType.CACHE_HIT, EvidenceType.SEMANTIC_SIMILARITY): 0.8,
    (EvidenceType.CACHE_HIT, EvidenceType.REGEX_MATCH): 0.2,
}


class InteractionMatrix:
    """
    Matriz de interacciones Jᵢⱼ entre tipos de evidencia.

    Almacena las interacciones como un dict simétrico.
    Soportado: consulta, actualización, aprendizaje desde feedback.
    """

    def __init__(self, interactions: dict[tuple[EvidenceType, EvidenceType], float] | None = None):
        # Usar defaultdict para que consultar cualquier par devuelva 0.0 por defecto
        self._matrix: dict[tuple[EvidenceType, EvidenceType], float] = defaultdict(float)
        if interactions:
            for (a, b), val in interactions.items():
                self.set(a, b, val)

    def init_defaults(self) -> None:
        """Cargar las interacciones por defecto."""
        for (a, b), val in _DEFAULT_INTERACTIONS.items():
            self.set(a, b, val)

    def get(self, t1: EvidenceType, t2: EvidenceType) -> float:
        """Obtener interacción entre dos tipos de evidencia."""
        # La matriz es simétrica — probar ambos órdenes
        val = self._matrix.get((t1, t2))
        if val is not None:
            return val
        val = self._matrix.get((t2, t1))
        if val is not None:
            return val
        return 0.0  # Independientes por defecto

    def set(self, t1: EvidenceType, t2: EvidenceType, value: float) -> None:
        """Establecer interacción entre dos tipos (matriz simétrica)."""
        if t1 == t2:
            return  # No hay auto-interacción
        self._matrix[(t1, t2)] = value
        self._matrix[(t2, t1)] = value  # Simetría

    def scale_all(self, factor: float) -> None:
        """Escalar todas las interacciones por un factor."""
        if factor == 0.0:
            self._matrix.clear()
            return
        for key in list(self._matrix.keys()):
            self._matrix[key] *= factor

    def learn_from_feedback(
        self,
        evidence_types: list[EvidenceType],
        was_correct: bool,
        learning_rate: float = 0.1,
    ) -> None:
        """
        Aprender desde feedback: ajustar Jᵢⱼ basado en si la decisión fue correcta.

        Si la decisión fue correcta → reforzar las interacciones que se usaron
        Si la decisión fue incorrecta → debilitar las interacciones que se usaron
        """
        delta = learning_rate if was_correct else -learning_rate
        n = len(evidence_types)
        for i in range(n):
            for j in range(i + 1, n):
                current = self.get(evidence_types[i], evidence_types[j])
                new_val = max(-3.0, min(3.0, current + delta))
                self.set(evidence_types[i], evidence_types[j], new_val)

    def to_dict(self) -> dict[str, float]:
        """Exportar como dict serializable."""
        return {
            f"{a.value}↔{b.value}": v
            for (a, b), v in self._matrix.items()
            if a.value < b.value  # Solo una dirección para evitar duplicados
        }

    def __len__(self) -> int:
        """Número de interacciones definidas."""
        unique_pairs = set()
        for (a, b) in self._matrix:
            unique_pairs.add((min(a.value, b.value), max(a.value, b.value)))
        return len(unique_pairs)

    def __repr__(self) -> str:
        return f"InteractionMatrix({len(self)} interactions)"
