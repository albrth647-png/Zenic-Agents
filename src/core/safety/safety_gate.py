"""SafetyGate — Gate inbypassable para acciones del sistema.

La IA solo dice YES/NO. NUNCA genera contenido.
DENY es FINAL — no se puede sobrepasar.

Reglas determinísticas que SIEMPRE se evalúan:
1. No modificar datos sin aprobación
2. No enviar mensajes ofensivos
3. No exponer datos sensibles
4. No ejecutar comandos del sistema

Solo si TODAS las reglas pasan, la IA puede evaluar (YES/NO).
Pero la IA NUNCA puede aprobar algo que las reglas denegaron.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SafetyVerdict(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    REVIEW = "review"  # Requiere revisión humana


@dataclass
class SafetyResult:
    """Resultado de la evaluación del SafetyGate."""

    approved: bool
    verdict: SafetyVerdict
    reason: str = ""
    rule_id: str = ""
    requires_human: bool = False

    def __post_init__(self):
        # DENY es inbypassable
        if self.verdict == SafetyVerdict.DENY:
            self.approved = False


# Reglas determinísticas — NUNCA se pueden sobrepasar
DENY_PATTERNS = [
    # No ejecutar comandos del sistema
    re.compile(r"(rm\s+-rf|del\s+/[sf]|format\s+[a-z]:)", re.IGNORECASE),
    # No modificar tablas del sistema
    re.compile(r"(DROP\s+TABLE|TRUNCATE\s+TABLE?)", re.IGNORECASE),
    # No exponer datos sensibles
    re.compile(r"(password|secret|token|api_key|credential)\s*[:=]", re.IGNORECASE),
    # No enviar mensajes ofensivos
    re.compile(r"(insult|threat|hate|harass)", re.IGNORECASE),
]

# Acciones que siempre requieren aprobación humana
REQUIRES_HUMAN = {"update", "delete", "execute", "system_command"}

# Acciones de bajo riesgo que no necesitan IA
LOW_RISK_ACTIONS = {"scan", "read", "notify", "suggest", "log"}


class SafetyGate:
    """SafetyGate inbypassable.

    Evaluación en 3 capas:
    1. Reglas determinísticas (siempre se evalúan, DENY es final)
    2. Policy check (requiere aprobación humana para alto riesgo)
    3. IA evaluación (solo YES/NO, nunca genera contenido)

    La IA NUNCA puede sobrepasar un DENY de las capas 1 o 2.
    """

    def __init__(self, policy_engine: PolicyEngine | None = None):  # noqa: F821  # TODO: Phase3 - verify import
        self._policy_engine = policy_engine
        self._denied_count = 0
        self._approved_count = 0
        self._review_count = 0
        logger.info("SafetyGate inicializado — DENY es inbypassable")

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> SafetyResult:
        """Evalúa una acción contra las 3 capas de seguridad.

        Capa 1: Reglas determinísticas — DENY es final
        Capa 2: Policy — requiere aprobación humana
        Capa 3: IA — solo YES/NO (no implementada, todo pasa sin IA)
        """
        context = context or {}

        # Capa 1: Reglas determinísticas
        deny_result = self._check_deterministic_rules(action, context)
        if deny_result:
            self._denied_count += 1
            logger.warning(f"SAFETY DENY (regla): {deny_result.reason}")
            return deny_result

        # Capa 2: Policy check
        policy_result = self._check_policy(action, context)
        if policy_result.verdict == SafetyVerdict.DENY:
            self._denied_count += 1
            logger.warning(f"SAFETY DENY (policy): {policy_result.reason}")
            return policy_result

        if policy_result.verdict == SafetyVerdict.REVIEW:
            self._review_count += 1
            logger.info(f"SAFETY REVIEW: {policy_result.reason}")
            return policy_result

        # Capa 3: IA evaluación (placeholder — en producción, IA dice YES/NO)
        # Por ahora, las acciones de bajo riesgo se aprueban automáticamente
        if action in LOW_RISK_ACTIONS:
            self._approved_count += 1
            return SafetyResult(
                approved=True,
                verdict=SafetyVerdict.APPROVE,
                reason="Acción de bajo riesgo aprobada automáticamente",
            )

        # Acciones de riesgo medio/alto requieren aprobación
        self._review_count += 1
        return SafetyResult(
            approved=False,
            verdict=SafetyVerdict.REVIEW,
            reason=f"Acción '{action}' requiere aprobación humana",
            requires_human=True,
        )

    def _check_deterministic_rules(self, action: str, context: dict[str, Any]) -> SafetyResult | None:
        """Capa 1: Reglas determinísticas. DENY es FINAL."""
        # Verificar acción contra patrones de denegación
        action_str = str(action) + " " + str(context.get("description", ""))

        for i, pattern in enumerate(DENY_PATTERNS):
            if pattern.search(action_str):
                return SafetyResult(
                    approved=False,
                    verdict=SafetyVerdict.DENY,
                    reason=f"Regla determinística violada (patrón {i + 1})",
                    rule_id=f"deny_pattern_{i + 1}",
                )

        # Verificar contexto
        step = context.get("step")
        if step and hasattr(step, "action_type"):
            if step.action_type == "delete":
                return SafetyResult(
                    approved=False,
                    verdict=SafetyVerdict.DENY,
                    reason="Acción DELETE bloqueada por regla determinística",
                    rule_id="deny_delete",
                )

        return None

    def _check_policy(self, action: str, context: dict[str, Any]) -> SafetyResult:
        """Capa 2: Policy check usando PolicyEngine si disponible."""
        if self._policy_engine:
            from src.core.safety.policy import PolicyAction

            policy_action = self._policy_engine.evaluate(action, context)

            if policy_action == PolicyAction.DENY:
                return SafetyResult(
                    approved=False,
                    verdict=SafetyVerdict.DENY,
                    reason=f"Acción '{action}' denegada por policy",
                    rule_id="policy_deny",
                )

            if policy_action == PolicyAction.RESTRICT:
                return SafetyResult(
                    approved=False,
                    verdict=SafetyVerdict.REVIEW,
                    reason=f"Acción '{action}' requiere aprobación humana según policy",
                    requires_human=True,
                )

            return SafetyResult(
                approved=True,
                verdict=SafetyVerdict.APPROVE,
                reason="Aprobado por policy",
            )

        # Sin PolicyEngine, usar reglas internas
        if action in REQUIRES_HUMAN:
            return SafetyResult(
                approved=False,
                verdict=SafetyVerdict.REVIEW,
                reason=f"Acción '{action}' requiere aprobación humana según policy",
                requires_human=True,
            )

        return SafetyResult(
            approved=True,
            verdict=SafetyVerdict.APPROVE,
            reason="Aprobado por policy",
        )

    def get_stats(self) -> dict[str, int]:
        """Estadísticas del SafetyGate."""
        return {
            "approved": self._approved_count,
            "denied": self._denied_count,
            "review": self._review_count,
        }
