"""TomorrowAppointmentMonitor — Recordatorio de citas de mañana.

Peso: WARNING (2) — Previene no-shows.

Escanea la tabla 'citas' en la BD LOCAL del usuario.
NO espera a que el usuario pregunte "¿tengo algo mañana?".
"""

from __future__ import annotations

import logging

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

logger = logging.getLogger(__name__)


class TomorrowAppointmentMonitor(BaseMonitor):
    """Monitor de citas de mañana — escanea la BD del usuario."""

    name = "tomorrow_appointment"
    weight = MonitorWeight.WARNING
    description = "Detecta citas programadas para mañana en la BD local"
    interval_seconds = 3600  # Cada hora

    def check(self) -> MonitorResult:
        """Busca citas de mañana en la BD del usuario."""
        appointments = self.scanner.scan_tomorrow_appointments()

        if not appointments:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "No hay citas para mañana"},
            )

        findings = []
        for apt in appointments:
            client = apt.get("cliente", apt.get("paciente", apt.get("nombre", "?")))
            date = apt.get("fecha", apt.get("date", "?"))
            time_val = apt.get("hora", apt.get("time", ""))
            findings.append(
                {
                    "type": "tomorrow_appointment",
                    "client": client,
                    "date": date,
                    "time": time_val,
                    "message": f"Cita mañana: {client} a las {time_val}" if time_val else f"Cita mañana: {client}",
                }
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_appointments": len(appointments),
                "source": "local_database",
            },
        )
