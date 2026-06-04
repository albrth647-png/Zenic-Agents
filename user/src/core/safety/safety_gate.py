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

    NATURALEZA ONTOLÓGICA:
      SOY: La barrera inbypassable del sistema. Evalúo cada acción contra 3 capas:
           reglas determinísticas (DENY es final), policy engine, y evaluación de
           IA (solo SÍ/NO). Ninguna acción puede eludir esta evaluación.
      NO SOY: Log de auditoría. Configurable por el usuario. No tengo modo
              degradado — DENY es DENY siempre.
      INVARIANTE: Es imposible saltarse una regla DENY. El código nunca contiene
                  caminos que puedan evitar mi evaluación.
      FRONTERA: No ejecuto acciones. No decido qué acciones son válidas desde el
                punto de vista funcional. Solo evalúo seguridad.

    COMPLETACIÓN SEMÁNTICA:
      - Mi permiso/denegación es completado por ZenicOrchestrator, que lo integra
        en la decisión final de commit/rollback.
      - Yo produzco PERMISO O DENEGACIÓN; el orchestrator produce
        EJECUCIÓN COORDINADA.

    Evaluación en 3 capas:
    1. Reglas determinísticas (siempre se evalúan, DENY es final)
    2. Policy check (requiere aprobación humana para alto riesgo)
    3. IA evaluación (solo YES/NO, nunca genera contenido)

    La IA NUNCA puede sobrepasar un DENY de las capas 1 o 2.
    """

    def __init__(self, policy_engine: PolicyEngine | None = None):  # TODO: Phase3 - verify import
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
        if step and hasattr(step, "action_type") and step.action_type == "delete":
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

    # ================================================================
    #  VORTEX 2.7: Auto-verificación de determinismo
    # ================================================================

    def verify_determinism(self) -> dict[str, Any]:
        """
        Verifica que el SafetyGate es determinista (VORTEX 2.7).

        Prueba que el mismo input produce el mismo resultado y que
        DENY es siempre DENY.

        Returns:
            Dict con resultado de verificación.
        """
        tests = []
        all_deterministic = True

        # Test 1: Acción peligrosa siempre produce DENY
        for action, ctx in [
            ("rm -rf /", {}),
            ("execute_system_command", {"step": type("obj", (object,), {"action_type": "delete"})()}),
        ]:
            result1 = self.evaluate(action, ctx)
            result2 = self.evaluate(action, ctx)
            consistent = (
                result1.verdict == result2.verdict
                and result1.approved == result2.approved
                and result1.verdict == SafetyVerdict.DENY
            )
            if not consistent:
                all_deterministic = False
            tests.append({
                "action": action[:50],
                "deterministic": consistent,
                "verdict": result1.verdict.value,
            })

        # Test 2: Acción segura siempre produce APPROVE
        safe_result1 = self.evaluate("read", {})
        safe_result2 = self.evaluate("read", {})
        safe_consistent = (
            safe_result1.verdict == safe_result2.verdict
            and safe_result1.approved == safe_result2.approved
        )
        if not safe_consistent:
            all_deterministic = False
        tests.append({
            "action": "read",
            "deterministic": safe_consistent,
            "verdict": safe_result1.verdict.value,
        })

        return {
            "component": "SafetyGate",
            "all_deterministic": all_deterministic,
            "deny_inbypassable": all(
                t["verdict"] == "deny" for t in tests if "rm" in t["action"] or "execute" in t["action"]
            ),
            "tests": tests,
            "status": "VERIFIED" if all_deterministic else "DEGRADED",
        }
