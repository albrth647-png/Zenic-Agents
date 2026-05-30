"""PolicyEngine — Motor de políticas de seguridad.

Define qué acciones están permitidas, restringidas o prohibidas
según el contexto, el nivel de autonomía y el riesgo.

Las políticas son determinísticas. No dependen de IA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PolicyAction(str, Enum):
    ALLOW = "allow"
    RESTRICT = "restrict"  # Requiere aprobación
    DENY = "deny"  # Siempre bloqueado


@dataclass
class Policy:
    """Una política de seguridad."""

    id: str
    name: str
    action_type: str
    policy_action: PolicyAction
    conditions: dict[str, Any]
    description: str


# Políticas por defecto
DEFAULT_POLICIES: list[Policy] = [
    Policy(
        "p001",
        "Leer datos locales",
        "scan",
        PolicyAction.ALLOW,
        {"always": True},
        "Permitir escaneo de datos locales sin restricción",
    ),
    Policy(
        "p002",
        "Notificar usuario",
        "notify",
        PolicyAction.ALLOW,
        {"always": True},
        "Permitir notificaciones al usuario",
    ),
    Policy(
        "p003",
        "Sugerir acción",
        "suggest",
        PolicyAction.ALLOW,
        {"always": True},
        "Permitir sugerencias sin restricción",
    ),
    Policy(
        "p004",
        "Actualizar datos",
        "update",
        PolicyAction.RESTRICT,
        {"requires_approval": True},
        "Actualizar datos requiere aprobación",
    ),
    Policy("p005", "Eliminar datos", "delete", PolicyAction.DENY, {"always": True}, "Eliminación siempre bloqueada"),
    Policy(
        "p006",
        "Ejecutar comando",
        "execute",
        PolicyAction.DENY,
        {"always": True},
        "Ejecución de comandos siempre bloqueada",
    ),
]


class PolicyEngine:
    """Motor de políticas de seguridad.

    Evalúa acciones contra las políticas definidas.
    Las políticas son determinísticas y no dependen de IA.
    """

    def __init__(self, policies: list[Policy] | None = None):
        self.policies = policies or DEFAULT_POLICIES
        self._policy_map = {p.action_type: p for p in self.policies}
        logger.info(f"PolicyEngine inicializado con {len(self.policies)} políticas")

    def evaluate(self, action_type: str, context: dict[str, Any] | None = None) -> PolicyAction:
        """Evalúa una acción contra las políticas."""
        context = context or {}

        policy = self._policy_map.get(action_type)
        if not policy:
            # Sin política = restrict por defecto
            logger.warning(f"Sin política para '{action_type}' — defaulting to RESTRICT")
            return PolicyAction.RESTRICT

        # Verificar condiciones
        if policy.policy_action == PolicyAction.ALLOW:
            return PolicyAction.ALLOW

        if policy.policy_action == PolicyAction.DENY:
            return PolicyAction.DENY

        # RESTRICT — verificar si hay contexto que lo permita
        if policy.policy_action == PolicyAction.RESTRICT:
            autonomy = context.get("autonomy_level", "supervised")
            if autonomy == "full_autonomous" and context.get("risk") == "low":
                return PolicyAction.ALLOW
            return PolicyAction.RESTRICT

        return PolicyAction.RESTRICT

    def add_policy(self, policy: Policy):
        """Añade una nueva política."""
        self.policies.append(policy)
        self._policy_map[policy.action_type] = policy
        logger.info(f"Política añadida: {policy.id} — {policy.name}")

    def get_all_policies(self) -> list[dict[str, Any]]:
        """Retorna todas las políticas."""
        return [
            {"id": p.id, "name": p.name, "action_type": p.action_type, "policy_action": p.policy_action.value}
            for p in self.policies
        ]
