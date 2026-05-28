"""StaleInventoryMonitor — Detecta inventario sin movimiento.

Peso: WARNING (2) — Capital inmovilizado.

Escanea la tabla 'productos' en la BD LOCAL buscando productos sin venta.
NO espera a que el usuario haga inventario manual.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class StaleInventoryMonitor(BaseMonitor):
    """Monitor de inventario estancado — escanea la BD del usuario."""

    name = "stale_inventory"
    weight = MonitorWeight.WARNING
    description = "Detecta productos sin venta en los últimos N días"
    interval_seconds = 7200  # Cada 2 horas

    def __init__(self, scanner: LocalDataScanner, stale_days: int = 90):
        super().__init__(scanner)
        self.stale_days = stale_days

    def check(self) -> MonitorResult:
        """Busca inventario estancado en la BD del usuario."""
        items = self.scanner.scan_stale_inventory(days=self.stale_days)

        if not items:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": f"Todo el inventario tiene movimiento en los últimos {self.stale_days} días"},
            )

        findings = []
        for item in items:
            name_val = item.get("nombre", item.get("name", item.get("producto", str(item.get("id", "?")))))
            last_sold = item.get("ultima_venta", item.get("last_sold", "nunca"))
            findings.append({
                "type": "stale_inventory",
                "product": name_val,
                "last_sold": last_sold,
                "days_threshold": self.stale_days,
                "message": f"Inventario estancado: {name_val} (última venta: {last_sold})",
            })

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_stale": len(items),
                "stale_days": self.stale_days,
                "source": "local_database",
            },
        )
