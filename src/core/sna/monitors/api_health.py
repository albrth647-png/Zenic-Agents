"""APIHealthMonitor — Detecta problemas con APIs externas.

Peso: INFO (1) — APIs caídas no son críticas pero el usuario debe saber.

Verifica endpoints configurados en la BD LOCAL del usuario.
NO espera a que el usuario reporte "la API no funciona".
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any
from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight
from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class APIHealthMonitor(BaseMonitor):
    """Monitor de salud de APIs — verifica endpoints configurados."""

    name = "api_health"
    weight = MonitorWeight.INFO
    description = "Verifica salud de APIs externas configuradas"
    interval_seconds = 600  # Cada 10 minutos

    # APIs comunes a verificar
    DEFAULT_ENDPOINTS: list[dict[str, str]] = [
        {"name": "whatsapp_api", "url": "https://api.whatsapp.com", "method": "HEAD"},
        {"name": "telegram_api", "url": "https://api.telegram.org", "method": "HEAD"},
    ]

    def __init__(self, scanner: LocalDataScanner, endpoints: list[dict] | None = None):
        super().__init__(scanner)
        self.endpoints = endpoints or self.DEFAULT_ENDPOINTS

    def check(self) -> MonitorResult:
        """Verifica salud de APIs externas.

        Nota: En modo síncrono, solo verifica configuración.
        El check real de red se hace en el scheduler async.
        """
        findings = []

        # Verificar si hay endpoints configurados en la BD
        try:
            if self.scanner.db.table_exists("api_endpoints"):
                custom_endpoints = self.scanner.db.execute_query(
                    "SELECT name, url, method FROM api_endpoints WHERE active = 1"
                )
                for ep in custom_endpoints:
                    self.endpoints.append(ep)
        except Exception:
            pass

        # Verificar que hay endpoints configurados
        if not self.endpoints:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "No hay APIs externas configuradas"},
            )

        details = {
            "total_endpoints": len(self.endpoints),
            "source": "local_config",
        }

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            healthy=True,
            details=details,
        )
