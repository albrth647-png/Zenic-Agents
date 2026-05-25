"""Autopilot — Sistema de automatización con objetivos.

4 templates + genérico:
1. CustomerRetention — Retener clientes en riesgo
2. InventoryOptimization — Optimizar inventario
3. RevenueRecovery — Recuperar ingresos perdidos
4. AppointmentReminder — Recordar citas
5. Generic — Objetivo custom

Autonomía:
- SUPERVISED: Siempre pide aprobación
- SEMI_AUTONOMOUS: Pide aprobación solo para alto riesgo
- FULL_AUTONOMOUS: Ejecuta y notifica

Pipeline: Blueprint→Policy→SafetyGate→Executor→Audit
"""

from src.core.autopilot.engine import AutopilotEngine

__all__ = ["AutopilotEngine"]
