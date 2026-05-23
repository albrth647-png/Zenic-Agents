"""BackupStatusMonitor — Detecta problemas con backups.

Peso: CRITICAL (3) — Sin backup = riesgo de pérdida total.

Escanea el filesystem LOCAL del usuario verificando backups.
NO espera a que el usuario necesite restaurar y descubra que no hay backup.
"""

from __future__ import annotations

import logging
from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight
from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class BackupStatusMonitor(BaseMonitor):
    """Monitor de backups — escanea el filesystem del usuario."""

    name = "backup_status"
    weight = MonitorWeight.CRITICAL
    description = "Detecta problemas con backups en el filesystem local"
    interval_seconds = 7200  # Cada 2 horas

    def check(self) -> MonitorResult:
        """Verifica estado de backups del usuario."""
        backup_info = self.scanner.scan_backup_status()
        status = backup_info.get("status", "unknown")

        if status == "ok":
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details=backup_info,
            )

        findings = []

        if status == "missing":
            findings.append({
                "type": "backup_missing",
                "message": "No existe directorio de backups",
                "recommendation": backup_info.get("recommendation", ""),
            })
        elif status == "empty":
            findings.append({
                "type": "backup_empty",
                "message": "Directorio de backups vacío — sin backups",
                "recommendation": backup_info.get("recommendation", ""),
            })
        elif status == "outdated":
            age = backup_info.get("latest_backup_age_hours", 0)
            findings.append({
                "type": "backup_outdated",
                "age_hours": age,
                "latest_backup": backup_info.get("latest_backup", ""),
                "message": f"Último backup tiene {age:.0f} horas",
                "recommendation": backup_info.get("recommendation", ""),
            })

        if not findings:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details=backup_info,
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details=backup_info,
        )
