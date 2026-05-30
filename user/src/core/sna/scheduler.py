"""SNAScheduler — Programa la ejecución periódica de monitores.

Cada monitor tiene su intervalo (5min, 10min, 30min, 1h, 2h).
El scheduler ejecuta los monitores según su intervalo y peso
(mayor peso = mayor prioridad).

Los monitores escanean datos LOCALES, NO leen de canales.
El scheduler es el latido del sistema nervioso autónomo.
"""

from __future__ import annotations

import heapq
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.core.sna.alert_manager import Alert, AlertManager
from src.core.sna.monitors import (
    APIHealthMonitor,
    BackupStatusMonitor,
    ConfigDriftMonitor,
    DataIntegrityMonitor,
    DiskSpaceMonitor,
    DuplicateRecordsMonitor,
    LowStockMonitor,
    OverdueInvoiceMonitor,
    SalesTrendMonitor,
    StaleInventoryMonitor,
    TomorrowAppointmentMonitor,
    UnpaidBalanceMonitor,
)
from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight
from src.core.sna.thresholds import ThresholdEngine

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


@dataclass(order=True)
class ScheduledCheck:
    """Check programado en la cola de prioridad."""

    next_run: float  # timestamp
    weight: int = field(compare=True)
    monitor_name: str = field(compare=False)
    interval: int = field(compare=False)

    @classmethod
    def create(cls, monitor: BaseMonitor, next_run: float | None = None) -> ScheduledCheck:
        return cls(
            next_run=next_run or time.time(),
            weight=-monitor.weight,  # Negativo para que CRITICAL (3) tenga mayor prioridad
            monitor_name=monitor.name,
            interval=monitor.interval_seconds,
        )


class SNAScheduler:
    """Scheduler de monitores SNA.

    Ejecuta monitores periódicamente según su intervalo y peso.
    Los resultados van al AlertManager.
    """

    def __init__(
        self,
        scanner: LocalDataScanner,
        alert_manager: AlertManager | None = None,
        threshold_engine: ThresholdEngine | None = None,
    ):
        self.scanner = scanner
        self.alert_manager = alert_manager or AlertManager()
        self.threshold_engine = threshold_engine or ThresholdEngine()

        self._monitors: dict[str, BaseMonitor] = {}
        self._schedule: list[ScheduledCheck] = []
        self._results: dict[str, MonitorResult] = {}
        self._running = False

        # Registrar todos los monitores
        self._register_default_monitors()

        logger.info(f"SNAScheduler inicializado con {len(self._monitors)} monitores")

    def _register_default_monitors(self):
        """Registra los 12 monitores por defecto."""
        monitors = [
            LowStockMonitor(self.scanner),
            OverdueInvoiceMonitor(self.scanner),
            TomorrowAppointmentMonitor(self.scanner),
            DiskSpaceMonitor(self.scanner),
            SalesTrendMonitor(self.scanner),
            StaleInventoryMonitor(self.scanner),
            UnpaidBalanceMonitor(self.scanner),
            DuplicateRecordsMonitor(self.scanner),
            ConfigDriftMonitor(self.scanner),
            BackupStatusMonitor(self.scanner),
            DataIntegrityMonitor(self.scanner),
            APIHealthMonitor(self.scanner),
        ]
        for monitor in monitors:
            self.register_monitor(monitor)

    def register_monitor(self, monitor: BaseMonitor):
        """Registra un monitor y lo programa para ejecución."""
        self._monitors[monitor.name] = monitor
        scheduled = ScheduledCheck.create(monitor)
        heapq.heappush(self._schedule, scheduled)
        logger.debug(
            f"Monitor registrado: {monitor.name} (intervalo={monitor.interval_seconds}s, peso={monitor.weight.name})"
        )

    def run_once(self) -> list[Alert]:
        """Ejecuta una ronda de checks según schedule.

        Ejecuta todos los monitores cuyo next_run <= now.
        Devuelve las alertas generadas.
        """
        now = time.time()
        alerts: list[Alert] = []

        # Ejecutar monitores que están listos
        executed = []
        while self._schedule and self._schedule[0].next_run <= now:
            scheduled = heapq.heappop(self._schedule)
            executed.append(scheduled)

        for scheduled in executed:
            monitor = self._monitors.get(scheduled.monitor_name)
            if not monitor:
                continue

            logger.debug(f"Ejecutando monitor: {monitor.name}")
            result = monitor.run()
            self._results[monitor.name] = result

            # Procesar resultado → generar alerta
            alert = self.alert_manager.process_result(result)
            if alert:
                alerts.append(alert)

            # Reprogramar
            next_run = now + monitor.interval_seconds
            new_scheduled = ScheduledCheck.create(monitor, next_run)
            heapq.heappush(self._schedule, new_scheduled)

        # Si no había monitores listos, ejecutar todos (primera vez)
        if not executed and not self._results:
            alerts = self.run_all()

        return alerts

    def run_all(self) -> list[Alert]:
        """Ejecuta TODOS los monitores inmediatamente."""
        alerts: list[Alert] = []
        logger.info(f"Ejecutando todos los monitores ({len(self._monitors)})...")

        for name, monitor in sorted(
            self._monitors.items(),
            key=lambda x: -x[1].weight,  # CRITICAL primero
        ):
            result = monitor.run()
            self._results[name] = result

            alert = self.alert_manager.process_result(result)
            if alert:
                alerts.append(alert)

        logger.info(f"Ronda completa: {len(alerts)} alertas generadas")
        return alerts

    def run_monitor(self, monitor_name: str) -> MonitorResult | None:
        """Ejecuta un monitor específico por nombre."""
        monitor = self._monitors.get(monitor_name)
        if not monitor:
            logger.warning(f"Monitor no encontrado: {monitor_name}")
            return None

        result = monitor.run()
        self._results[monitor_name] = result
        return result

    def get_results(self) -> dict[str, MonitorResult]:
        """Obtiene los resultados de la última ejecución."""
        return self._results.copy()

    def get_health_summary(self) -> dict[str, Any]:
        """Resumen de salud del sistema basado en los monitores."""
        total = len(self._results)
        healthy = sum(1 for r in self._results.values() if r.healthy)
        unhealthy = total - healthy

        return {
            "total_monitors": len(self._monitors),
            "monitors_run": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "health_percent": round((healthy / total * 100) if total > 0 else 100, 1),
            "issues_by_severity": {
                "critical": sum(
                    1 for r in self._results.values() if not r.healthy and r.weight == MonitorWeight.CRITICAL
                ),
                "warning": sum(
                    1 for r in self._results.values() if not r.healthy and r.weight == MonitorWeight.WARNING
                ),
                "info": sum(1 for r in self._results.values() if not r.healthy and r.weight == MonitorWeight.INFO),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def stop(self):
        """Detiene el scheduler."""
        self._running = False
        logger.info("SNAScheduler detenido")
