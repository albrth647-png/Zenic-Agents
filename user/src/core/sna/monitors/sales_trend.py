"""SalesTrendMonitor — Detecta caídas en tendencia de ventas.

Peso: WARNING (2) — Caída de ventas = problema de negocio.

Compara ventas de la última semana vs semana anterior en la BD LOCAL.
NO espera a que el usuario note la caída.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class SalesTrendMonitor(BaseMonitor):
    """Monitor de tendencia de ventas — compara semanas en la BD del usuario."""

    name = "sales_trend"
    weight = MonitorWeight.WARNING
    description = "Detecta caídas en tendencia de ventas comparando semanas"
    interval_seconds = 3600  # Cada hora

    def __init__(self, scanner: LocalDataScanner, drop_threshold_percent: float = 30.0):
        super().__init__(scanner)
        self.drop_threshold_percent = drop_threshold_percent

    def check(self) -> MonitorResult:
        """Compara ventas última semana vs anterior en la BD del usuario."""
        trend = self.scanner.scan_sales_trend(days=30)

        if not trend or len(trend) < 14:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "Datos insuficientes para análisis de tendencia", "data_points": len(trend)},
            )

        # Calcular total de los últimos 7 días vs 7 días anteriores
        recent = trend[-7:]
        previous = trend[-14:-7]

        recent_total = sum(float(r.get("total", 0)) for r in recent)
        previous_total = sum(float(r.get("total", 0)) for r in previous)

        if previous_total == 0:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "Semana anterior sin ventas", "recent_total": recent_total},
            )

        change_percent = ((recent_total - previous_total) / previous_total) * 100

        if change_percent < -self.drop_threshold_percent:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                findings=[{
                    "type": "sales_drop",
                    "recent_total": round(recent_total, 2),
                    "previous_total": round(previous_total, 2),
                    "change_percent": round(change_percent, 1),
                    "message": f"Caída de ventas: {abs(change_percent):.1f}% vs semana anterior",
                }],
                healthy=False,
                details={
                    "recent_total": recent_total,
                    "previous_total": previous_total,
                    "change_percent": change_percent,
                    "source": "local_database",
                },
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            healthy=True,
            details={
                "recent_total": recent_total,
                "previous_total": previous_total,
                "change_percent": round(change_percent, 1),
                "source": "local_database",
            },
        )
