"""BaseMonitor — Clase base para todos los monitores SNA.

Cada monitor:
1. Usa LocalDataScanner para acceder a datos LOCALES del usuario
2. Ejecuta su check() periódicamente
3. Devuelve MonitorResult con hallazgos y severidad
4. NO depende de canales — ve directamente en la BD/filesystem
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class MonitorWeight(IntEnum):
    """Peso del monitor — determina prioridad y frecuencia de escaneo."""
    CRITICAL = 3  # Puede causar pérdida de datos/dinero
    WARNING = 2   # Afecta operaciones
    INFO = 1      # Información útil


@dataclass
class MonitorResult:
    """Resultado de un monitor check.

    Attributes:
        monitor_name: Nombre del monitor
        weight: Peso del monitor (determina severidad)
        findings: Lista de problemas encontrados
        healthy: True si no hay problemas
        details: Datos adicionales para diagnóstico
        scanned_at: Timestamp del escaneo
    """
    monitor_name: str
    weight: MonitorWeight
    findings: list[dict[str, Any]] = field(default_factory=list)
    healthy: bool = True
    details: dict[str, Any] = field(default_factory=dict)
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def severity(self) -> str:
        """Severidad calculada basada en peso y hallazgos."""
        if self.healthy:
            return "ok"
        if self.weight == MonitorWeight.CRITICAL:
            return "critical"
        if self.weight == MonitorWeight.WARNING:
            return "warning"
        return "info"

    @property
    def finding_count(self) -> int:
        return len(self.findings)


class BaseMonitor(ABC):
    """Clase base abstracta para monitores SNA.

    Los monitores escanean datos LOCALES del usuario usando LocalDataScanner.
    NO leen de canales. Son proactivos, no reactivos.
    """

    name: str = "base"
    weight: MonitorWeight = MonitorWeight.INFO
    description: str = "Monitor base"
    interval_seconds: int = 300  # Default: cada 5 minutos

    def __init__(self, scanner: LocalDataScanner):
        self.scanner = scanner
        self._last_result: MonitorResult | None = None
        logger.debug(f"Monitor {self.name} inicializado (peso={self.weight.name})")

    @abstractmethod
    def check(self) -> MonitorResult:
        """Ejecuta el check del monitor.

        DEBE usar self.scanner para consultar datos locales.
        NO debe leer de canales.
        """
        ...

    def run(self) -> MonitorResult:
        """Ejecuta el check con manejo de errores."""
        try:
            result = self.check()
            self._last_result = result
            if not result.healthy:
                logger.warning(
                    f"[{self.name}] {result.finding_count} hallazgo(s) — severidad={result.severity}"
                )
            else:
                logger.debug(f"[{self.name}] Saludable")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Error en check: {e}")
            result = MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,  # No generar alerta por error de monitor
                details={"error": str(e)},
            )
            self._last_result = result
            return result

    @property
    def last_result(self) -> MonitorResult | None:
        return self._last_result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, weight={self.weight.name})"
