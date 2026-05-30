"""DiskSpaceMonitor — Detecta espacio en disco bajo.

Peso: CRITICAL (3) — Disco lleno = pérdida de datos.

Escanea el filesystem LOCAL del usuario.
NO espera a que la app se caiga.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class DiskSpaceMonitor(BaseMonitor):
    """Monitor de espacio en disco — escanea el filesystem del usuario."""

    name = "disk_space"
    weight = MonitorWeight.CRITICAL
    description = "Detecta espacio en disco bajo en el filesystem local"
    interval_seconds = 300  # Cada 5 minutos

    def __init__(self, scanner: LocalDataScanner, critical_percent: float = 95.0, warning_percent: float = 85.0):
        super().__init__(scanner)
        self.critical_percent = critical_percent
        self.warning_percent = warning_percent

    def check(self) -> MonitorResult:
        """Verifica espacio en disco del usuario."""
        disk_info = self.scanner.scan_disk_space()

        if disk_info.get("status") == "error":
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"error": disk_info.get("error", "unknown")},
            )

        percent = disk_info.get("percent_used", 0)

        if percent >= self.critical_percent:
            return MonitorResult(
                monitor_name=self.name,
                weight=MonitorWeight.CRITICAL,
                findings=[
                    {
                        "type": "disk_critical",
                        "percent_used": percent,
                        "free_gb": disk_info.get("free_gb", 0),
                        "message": f"DISCO CRÍTICO: {percent}% usado, {disk_info.get('free_gb', 0)}GB libre",
                    }
                ],
                healthy=False,
                details=disk_info,
            )

        if percent >= self.warning_percent:
            return MonitorResult(
                monitor_name=self.name,
                weight=MonitorWeight.WARNING,
                findings=[
                    {
                        "type": "disk_warning",
                        "percent_used": percent,
                        "free_gb": disk_info.get("free_gb", 0),
                        "message": f"Disco bajo: {percent}% usado, {disk_info.get('free_gb', 0)}GB libre",
                    }
                ],
                healthy=False,
                details=disk_info,
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            healthy=True,
            details=disk_info,
        )
