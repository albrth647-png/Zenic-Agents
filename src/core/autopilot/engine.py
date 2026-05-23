"""AutopilotEngine — Motor de automatización con objetivos.

Recibe objetivos del SNA o del usuario, genera un plan,
lo ejecuta paso a paso, y ajusta según feedback.

IA ENJAULADA: La IA solo dice YES/NO en el SafetyGate.
Nunca genera contenido ni toma decisiones ejecutivas.
"""

from __future__ import annotations

import logging
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.data.local_scanner import LocalDataScanner
from src.core.safety.safety_gate import SafetyGate
from src.core.sna.alert_manager import AlertSeverity

logger = logging.getLogger(__name__)


class AutonomyLevel(str, Enum):
    SUPERVISED = "supervised"
    SEMI_AUTONOMOUS = "semi_autonomous"
    FULL_AUTONOMOUS = "full_autonomous"


class GoalTemplate(str, Enum):
    CUSTOMER_RETENTION = "customer_retention"
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    REVENUE_RECOVERY = "revenue_recovery"
    APPOINTMENT_REMINDER = "appointment_reminder"
    GENERIC = "generic"


@dataclass
class Goal:
    """Objetivo del Autopilot."""
    id: str
    template: GoalTemplate
    description: str
    target_metric: str
    target_value: Any
    deadline: str = ""
    priority: int = 2  # 1=baja, 2=media, 3=alta
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "sna"  # "sna" o "user"


@dataclass
class ActionStep:
    """Un paso en el plan de acción."""
    id: str
    goal_id: str
    step_number: int
    action_type: str
    description: str
    risk: str = "low"  # "low", "medium", "high"
    requires_approval: bool = False
    status: str = "pending"  # "pending", "approved", "executing", "done", "failed", "skipped"
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """Plan de acción generado por el Autopilot."""
    id: str
    goal: Goal
    steps: list[ActionStep] = field(default_factory=list)
    status: str = "draft"  # "draft", "approved", "executing", "completed", "failed"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AutopilotEngine:
    """Motor de automatización con objetivos.

    Pipeline:
        Goal → Planner → Plan → Policy Check → SafetyGate → Executor → Audit → Feedback

    El Autopilot USA datos locales (via LocalDataScanner) para:
    - Generar planes basados en datos reales
    - Ejecutar acciones que modifican datos
    - Verificar resultados después de ejecutar
    """

    def __init__(
        self,
        scanner: LocalDataScanner,
        safety_gate: SafetyGate | None = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.SEMI_AUTONOMOUS,
        on_action: Callable[[dict], None] | None = None,
    ):
        self.scanner = scanner
        self.safety_gate = safety_gate or SafetyGate()
        self.autonomy_level = autonomy_level
        self._on_action = on_action

        self._goals: dict[str, Goal] = {}
        self._plans: dict[str, Plan] = {}
        self._goal_counter = 0

        logger.info(f"AutopilotEngine inicializado (autonomía={autonomy_level.value})")

    def create_goal(
        self,
        template: GoalTemplate,
        description: str,
        target_metric: str,
        target_value: Any,
        source: str = "sna",
        priority: int = 2,
    ) -> Goal:
        """Crea un nuevo objetivo."""
        self._goal_counter += 1
        goal = Goal(
            id=f"goal_{self._goal_counter}",
            template=template,
            description=description,
            target_metric=target_metric,
            target_value=target_value,
            source=source,
            priority=priority,
        )
        self._goals[goal.id] = goal
        logger.info(f"Objetivo creado: {goal.id} — {description}")
        return goal

    def generate_plan(self, goal_id: str) -> Plan | None:
        """Genera un plan de acción para un objetivo."""
        goal = self._goals.get(goal_id)
        if not goal:
            logger.error(f"Objetivo no encontrado: {goal_id}")
            return None

        # Generar pasos según template
        steps = self._generate_steps(goal)

        plan = Plan(id=f"plan_{goal_id}", goal=goal, steps=steps)
        self._plans[plan.id] = plan

        logger.info(f"Plan generado: {plan.id} con {len(steps)} pasos")
        return plan

    def execute_plan(self, plan_id: str) -> dict[str, Any]:
        """Ejecuta un plan paso a paso."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "error": f"Plan no encontrado: {plan_id}"}

        plan.status = "executing"
        results = []

        for step in plan.steps:
            if step.status in ("done", "skipped"):
                continue

            # Policy check: ¿requiere aprobación según autonomía?
            step.requires_approval = self._needs_approval(step)

            if step.requires_approval:
                step.status = "awaiting_approval"
                logger.info(f"Paso {step.step_number} requiere aprobación: {step.description}")
                # Notificar al usuario via AutopilotChannelInterceptor
                if self._on_action:
                    self._on_action({
                        "type": "approval_required",
                        "plan_id": plan_id,
                        "step": step,
                    })
                continue

            # SafetyGate check
            gate_result = self.safety_gate.evaluate(
                action=step.action_type,
                context={"step": step, "goal": plan.goal},
            )

            if not gate_result.approved:
                step.status = "blocked"
                step.result = {"blocked": True, "reason": gate_result.reason}
                logger.warning(f"Paso {step.step_number} bloqueado por SafetyGate: {gate_result.reason}")
                continue

            # Execute
            step.status = "executing"
            try:
                result = self._execute_step(step)
                step.status = "done"
                step.result = result
                results.append(result)

                if self._on_action:
                    self._on_action({"type": "step_completed", "step": step, "result": result})

            except Exception as e:
                step.status = "failed"
                step.result = {"error": str(e)}
                logger.error(f"Paso {step.step_number} falló: {e}")

        # Verificar si todos los pasos terminaron
        all_done = all(s.status in ("done", "skipped") for s in plan.steps)
        any_failed = any(s.status == "failed" for s in plan.steps)

        plan.status = "completed" if all_done else ("failed" if any_failed else "partial")

        return {
            "success": all_done,
            "plan_status": plan.status,
            "steps_completed": sum(1 for s in plan.steps if s.status == "done"),
            "steps_failed": sum(1 for s in plan.steps if s.status == "failed"),
            "results": results,
        }

    def get_status(self) -> dict[str, Any]:
        """Estado actual del Autopilot."""
        return {
            "autonomy_level": self.autonomy_level.value,
            "total_goals": len(self._goals),
            "total_plans": len(self._plans),
            "active_goals": [g.id for g in self._goals.values()],
            "plans_by_status": {
                status: sum(1 for p in self._plans.values() if p.status == status)
                for status in ["draft", "approved", "executing", "completed", "failed"]
            },
        }

    # ------------------------------------------------------------------ #
    #  Métodos privados                                                   #
    # ------------------------------------------------------------------ #

    def _needs_approval(self, step: ActionStep) -> bool:
        """Determina si un paso necesita aprobación según autonomía."""
        if self.autonomy_level == AutonomyLevel.SUPERVISED:
            return True
        if self.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS:
            return step.risk in ("medium", "high")
        return False  # FULL_AUTONOMOUS

    def _generate_steps(self, goal: Goal) -> list[ActionStep]:
        """Genera pasos según el template del objetivo."""
        templates = {
            GoalTemplate.CUSTOMER_RETENTION: self._template_customer_retention,
            GoalTemplate.INVENTORY_OPTIMIZATION: self._template_inventory,
            GoalTemplate.REVENUE_RECOVERY: self._template_revenue_recovery,
            GoalTemplate.APPOINTMENT_REMINDER: self._template_appointment,
            GoalTemplate.GENERIC: self._template_generic,
        }

        generator = templates.get(goal.template, self._template_generic)
        return generator(goal)

    def _template_customer_retention(self, goal: Goal) -> list[ActionStep]:
        """Template: Retener clientes en riesgo."""
        return [
            ActionStep(id=f"{goal.id}_s1", goal_id=goal.id, step_number=1,
                       action_type="scan", description="Identificar clientes en riesgo usando datos locales",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s2", goal_id=goal.id, step_number=2,
                       action_type="notify", description="Enviar recordatorio proactivo al cliente",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s3", goal_id=goal.id, step_number=3,
                       action_type="update", description="Marcar cliente como contactado en la BD",
                       risk="medium"),
        ]

    def _template_inventory(self, goal: Goal) -> list[ActionStep]:
        """Template: Optimizar inventario."""
        return [
            ActionStep(id=f"{goal.id}_s1", goal_id=goal.id, step_number=1,
                       action_type="scan", description="Escaneo de inventario actual desde BD local",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s2", goal_id=goal.id, step_number=2,
                       action_type="notify", description="Notificar productos con stock bajo",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s3", goal_id=goal.id, step_number=3,
                       action_type="suggest", description="Sugerir pedido de reabastecimiento",
                       risk="medium"),
        ]

    def _template_revenue_recovery(self, goal: Goal) -> list[ActionStep]:
        """Template: Recuperar ingresos perdidos."""
        return [
            ActionStep(id=f"{goal.id}_s1", goal_id=goal.id, step_number=1,
                       action_type="scan", description="Buscar facturas vencidas en BD local",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s2", goal_id=goal.id, step_number=2,
                       action_type="notify", description="Enviar recordatorio de pago al cliente",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s3", goal_id=goal.id, step_number=3,
                       action_type="update", description="Actualizar estado de factura en BD",
                       risk="medium"),
        ]

    def _template_appointment(self, goal: Goal) -> list[ActionStep]:
        """Template: Recordar citas."""
        return [
            ActionStep(id=f"{goal.id}_s1", goal_id=goal.id, step_number=1,
                       action_type="scan", description="Buscar citas de mañana en BD local",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s2", goal_id=goal.id, step_number=2,
                       action_type="notify", description="Enviar recordatorio de cita",
                       risk="low"),
        ]

    def _template_generic(self, goal: Goal) -> list[ActionStep]:
        """Template: Objetivo genérico."""
        return [
            ActionStep(id=f"{goal.id}_s1", goal_id=goal.id, step_number=1,
                       action_type="scan", description=f"Analizar datos locales para: {goal.description}",
                       risk="low"),
            ActionStep(id=f"{goal.id}_s2", goal_id=goal.id, step_number=2,
                       action_type="notify", description="Notificar hallazgo al usuario",
                       risk="low"),
        ]

    def _execute_step(self, step: ActionStep) -> dict[str, Any]:
        """Ejecuta un paso del plan. Determinístico."""
        action_map = {
            "scan": self._action_scan,
            "notify": self._action_notify,
            "update": self._action_update,
            "suggest": self._action_suggest,
        }

        executor = action_map.get(step.action_type, self._action_generic)
        return executor(step)

    def _action_scan(self, step: ActionStep) -> dict[str, Any]:
        """Acción de escaneo — lee datos locales."""
        # El escaneo usa LocalDataScanner directamente
        scan_result = self.scanner.full_scan()
        return {"action": "scan", "data": scan_result}

    def _action_notify(self, step: ActionStep) -> dict[str, Any]:
        """Acción de notificación — delega al ProactiveChannelBridge."""
        if self._on_action:
            self._on_action({"type": "send_notification", "step": step})
        return {"action": "notify", "message": step.description}

    def _action_update(self, step: ActionStep) -> dict[str, Any]:
        """Acción de actualización — modifica datos locales."""
        # Solo si está aprobado por SafetyGate
        return {"action": "update", "description": step.description, "status": "pending_approval"}

    def _action_suggest(self, step: ActionStep) -> dict[str, Any]:
        """Acción de sugerencia — no modifica nada."""
        return {"action": "suggest", "description": step.description}

    def _action_generic(self, step: ActionStep) -> dict[str, Any]:
        """Acción genérica."""
        return {"action": step.action_type, "description": step.description}
