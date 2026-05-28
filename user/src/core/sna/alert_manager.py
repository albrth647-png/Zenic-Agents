"""AlertManager — Gestiona alertas del SNA con deduplicación y rate-limit.

Recibe MonitorResults de los monitores y genera alertas limpias.
Las alertas van a ProactiveChannelBridge para notificar al usuario.

Deduplicación: La misma alerta no se repite dentro de la ventana de cooldown.
Rate-limit: No más de N alertas por minuto para no spamear al usuario.
Severidad: Se rutea según peso del monitor (critical → WhatsApp, warning → Telegram, info → log).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.sna.monitors.base import MonitorResult

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    LOG = "log"


@dataclass
class Alert:
    """Alerta generada por un monitor."""

    id: str
    monitor_name: str
    severity: AlertSeverity
    channel: AlertChannel
    message: str
    findings: list[dict[str, Any]]
    details: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            # Fingerprint para deduplicación: monitor + tipo de finding
            finding_types = sorted({f.get("type", "") for f in self.findings})
            self.fingerprint = f"{self.monitor_name}:{':'.join(finding_types)}"


@dataclass
class AlertStats:
    """Estadísticas del AlertManager."""

    total_alerts: int = 0
    alerts_by_severity: dict[str, int] = field(default_factory=dict)
    alerts_by_monitor: dict[str, int] = field(default_factory=dict)
    suppressed_by_dedup: int = 0
    suppressed_by_rate: int = 0


class AlertManager:
    """Gestiona alertas con deduplicación y rate-limit.

    Ruteo por severidad:
        CRITICAL → WhatsApp (canal primario del usuario)
        WARNING  → Telegram (canal secundario)
        INFO     → Log solamente
    """

    def __init__(
        self,
        cooldown_seconds: int = 1800,  # 30 min entre alertas duplicadas
        rate_limit_per_minute: int = 5,  # Max 5 alertas/min
        default_channel: AlertChannel = AlertChannel.TELEGRAM,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.default_channel = default_channel

        # Estado interno
        self._recent_alerts: dict[str, float] = {}  # fingerprint → timestamp
        self._alert_times: list[float] = []  # timestamps para rate-limit
        self._stats = AlertStats()
        self._pending_alerts: list[Alert] = []

        logger.info(f"AlertManager inicializado (cooldown={cooldown_seconds}s, rate_limit={rate_limit_per_minute}/min)")

    def process_result(self, result: MonitorResult) -> Alert | None:
        """Procesa un MonitorResult y genera una Alert si corresponde.

        Returns:
            Alert si se generó, None si fue suprimida por dedup/rate-limit
        """
        if result.healthy:
            return None

        # Mapear severidad
        severity = self._map_severity(result.severity)
        channel = self._route_channel(severity)

        # Crear alerta
        alert = Alert(
            id=f"{result.monitor_name}_{int(time.time())}",
            monitor_name=result.monitor_name,
            severity=severity,
            channel=channel,
            message=self._build_message(result),
            findings=result.findings,
            details=result.details,
        )

        # Deduplicación
        if self._is_duplicate(alert.fingerprint):
            self._stats.suppressed_by_dedup += 1
            logger.debug(f"Alerta deduplicada: {alert.fingerprint}")
            return None

        # Rate-limit
        if self._is_rate_limited():
            self._stats.suppressed_by_rate += 1
            logger.debug(f"Alerta rate-limited: {alert.monitor_name}")
            return None

        # Registrar
        self._recent_alerts[alert.fingerprint] = time.time()
        self._alert_times.append(time.time())
        self._stats.total_alerts += 1
        self._stats.alerts_by_severity[severity.value] = self._stats.alerts_by_severity.get(severity.value, 0) + 1
        self._stats.alerts_by_monitor[result.monitor_name] = (
            self._stats.alerts_by_monitor.get(result.monitor_name, 0) + 1
        )

        self._pending_alerts.append(alert)
        logger.info(f"Alerta generada: [{severity.value}] {result.monitor_name} → {channel.value}")

        return alert

    def get_pending_alerts(self) -> list[Alert]:
        """Obtiene alertas pendientes y limpia la lista."""
        alerts = self._pending_alerts.copy()
        self._pending_alerts.clear()
        return alerts

    def get_stats(self) -> AlertStats:
        return self._stats

    # ------------------------------------------------------------------ #
    #  Métodos privados                                                   #
    # ------------------------------------------------------------------ #

    def _map_severity(self, severity_str: str) -> AlertSeverity:
        """Mapea string de severidad a enum."""
        mapping = {
            "ok": AlertSeverity.OK,
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "critical": AlertSeverity.CRITICAL,
        }
        return mapping.get(severity_str, AlertSeverity.INFO)

    def _route_channel(self, severity: AlertSeverity) -> AlertChannel:
        """Rutea alerta a canal según severidad."""
        if severity == AlertSeverity.CRITICAL:
            return AlertChannel.WHATSAPP
        if severity == AlertSeverity.WARNING:
            return self.default_channel
        return AlertChannel.LOG

    def _build_message(self, result: MonitorResult) -> str:
        """Construye mensaje de alerta legible."""
        lines = [f"⚠ {result.monitor_name.replace('_', ' ').title()}"]
        for finding in result.findings[:5]:  # Max 5 findings en mensaje
            lines.append(f"  • {finding.get('message', str(finding))}")
        if result.finding_count > 5:
            lines.append(f"  ... y {result.finding_count - 5} más")
        return "\n".join(lines)

    def _is_duplicate(self, fingerprint: str) -> bool:
        """Verifica si la alerta es duplicada (dentro de cooldown)."""
        last_time = self._recent_alerts.get(fingerprint)
        if last_time is None:
            return False
        return (time.time() - last_time) < self.cooldown_seconds

    def _is_rate_limited(self) -> bool:
        """Verifica si se excedió el rate-limit."""
        now = time.time()
        # Limpiar timestamps viejos (más de 60s)
        self._alert_times = [t for t in self._alert_times if now - t < 60]
        return len(self._alert_times) >= self.rate_limit_per_minute

    def cleanup(self):
        """Limpia estado expirado."""
        now = time.time()
        expired = [fp for fp, t in self._recent_alerts.items() if now - t > self.cooldown_seconds]
        for fp in expired:
            del self._recent_alerts[fp]
        self._alert_times = [t for t in self._alert_times if now - t < 60]
