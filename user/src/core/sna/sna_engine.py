"""SNAEngine — Fachada del Sistema Nervioso Autónomo.

Unifica LocalDataScanner + SNAScheduler + AlertManager + ThresholdEngine.

Uso:
    engine = SNAEngine()
    alerts = engine.check()           # Ejecutar ronda de checks
    alerts = engine.full_scan()       # Escaneo completo
    summary = engine.health_summary() # Estado del sistema
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.core.sna.alert_manager import Alert, AlertManager
from src.core.sna.scheduler import SNAScheduler
from src.core.sna.thresholds import ThresholdEngine
from src.data.local_scanner import LocalDataScanner

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class SNAEngine:
    """Fachada del Sistema Nervioso Autónomo.

    El SNA escanea datos LOCALES del usuario:
    - No es adivino: pregunta directamente a la BD y filesystem
    - No depende de canales: detecta problemas antes de que se manifiesten
    - Es configurable: el usuario define sus umbrales
    """

    def __init__(
        self,
        db_path: str | None = None,
        base_path: str | None = None,
        config_path: str | None = None,
        on_alert: Callable[[Alert], None] | None = None,
    ):
        self.scanner = LocalDataScanner(db_path=db_path, base_path=base_path)
        self.threshold_engine = ThresholdEngine(config_path=config_path)
        self.alert_manager = AlertManager()
        self.scheduler = SNAScheduler(
            scanner=self.scanner,
            alert_manager=self.alert_manager,
            threshold_engine=self.threshold_engine,
        )
        self._on_alert = on_alert
        logger.info("SNAEngine inicializado — ojos sobre datos locales")

    def check(self) -> list[Alert]:
        """Ejecuta una ronda de checks del scheduler."""
        alerts = self.scheduler.run_once()
        for alert in alerts:
            if self._on_alert:
                self._on_alert(alert)
        return alerts

    def full_scan(self) -> list[Alert]:
        """Ejecuta escaneo completo de todos los monitores."""
        alerts = self.scheduler.run_all()
        for alert in alerts:
            if self._on_alert:
                self._on_alert(alert)
        return alerts

    def scan_local_data(self) -> dict[str, Any]:
        """Ejecuta un escaneo completo de datos locales (BD + filesystem)."""
        return self.scanner.full_scan()

    def health_summary(self) -> dict[str, Any]:
        """Resumen de salud del sistema."""
        return self.scheduler.get_health_summary()

    def get_alerts(self) -> list[Alert]:
        """Obtiene alertas pendientes."""
        return self.alert_manager.get_pending_alerts()

    def get_stats(self) -> dict[str, Any]:
        """Estadísticas del sistema."""
        stats = self.alert_manager.get_stats()
        return {
            "total_alerts": stats.total_alerts,
            "suppressed_by_dedup": stats.suppressed_by_dedup,
            "suppressed_by_rate": stats.suppressed_by_rate,
            "alerts_by_severity": stats.alerts_by_severity,
            "alerts_by_monitor": stats.alerts_by_monitor,
        }

    def set_alert_callback(self, callback: Callable[[Alert], None]):
        """Establece callback para cuando se genera una alerta."""
        self._on_alert = callback

    def close(self):
        """Cierra el engine y sus recursos."""
        self.scheduler.stop()
        self.scanner.close()
        logger.info("SNAEngine cerrado")

    def __repr__(self) -> str:
        return f"SNAEngine(monitors={len(self.scheduler._monitors)})"
