"""LowStockMonitor — Detecta productos con stock bajo.

Peso: CRITICAL (3) — Puede causar pérdida de ventas.

Escanea la tabla 'productos' en la BD LOCAL del usuario.
NO espera a que el usuario reporte "no tengo stock" por WhatsApp.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class LowStockMonitor(BaseMonitor):
    """Monitor de stock bajo — escanea la BD del usuario directamente."""

    name = "low_stock"
    weight = MonitorWeight.CRITICAL
    description = "Detecta productos con stock bajo en la BD local"
    interval_seconds = 300  # Cada 5 minutos

    def __init__(self, scanner: LocalDataScanner, threshold: int = 5):
        super().__init__(scanner)
        self.threshold = threshold

    def check(self) -> MonitorResult:
        """Busca productos con stock bajo en la BD del usuario."""
        items = self.scanner.scan_low_stock(threshold=self.threshold)

        if not items:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": f"Todos los productos tienen stock > {self.threshold}"},
            )

        findings = []
        for item in items:
            stock_val = item.get("stock", item.get("cantidad", item.get("inventario", "?")))
            name_val = item.get("nombre", item.get("name", item.get("producto", str(item.get("id", "?")))))
            findings.append(
                {
                    "type": "low_stock",
                    "product": name_val,
                    "current_stock": stock_val,
                    "threshold": self.threshold,
                    "message": f"Stock bajo: {name_val} tiene {stock_val} unidades (mínimo: {self.threshold})",
                }
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_low_stock": len(items),
                "threshold": self.threshold,
                "source": "local_database",
            },
        )
