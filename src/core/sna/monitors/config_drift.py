"""ConfigDriftMonitor — Detecta problemas en archivos de configuración.

Peso: WARNING (2) — Config malformada = app no funciona.

Escanea el filesystem LOCAL del usuario buscando configs faltantes o rotas.
NO espera a que la app falle al iniciar.
"""

from __future__ import annotations

import logging

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

logger = logging.getLogger(__name__)


class ConfigDriftMonitor(BaseMonitor):
    """Monitor de configuración — escanea el filesystem del usuario."""

    name = "config_drift"
    weight = MonitorWeight.WARNING
    description = "Detecta problemas en archivos de configuración locales"
    interval_seconds = 3600  # Cada hora

    def check(self) -> MonitorResult:
        """Verifica archivos de configuración del usuario."""
        configs = self.scanner.scan_config_health()

        findings = []
        for config in configs:
            path = config.get("path", "?")
            exists = config.get("exists", False)

            if not exists:
                findings.append(
                    {
                        "type": "config_missing",
                        "path": path,
                        "message": f"Config faltante: {path}",
                    }
                )
                continue

            if config.get("valid_json") is False:
                findings.append(
                    {
                        "type": "config_malformed",
                        "path": path,
                        "error": config.get("json_error", "unknown"),
                        "message": f"Config malformada: {path} — {config.get('json_error', '')}",
                    }
                )

            if config.get("readable") is False:
                findings.append(
                    {
                        "type": "config_unreadable",
                        "path": path,
                        "message": f"Config sin permisos de lectura: {path}",
                    }
                )

        if not findings:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "Todas las configuraciones están correctas"},
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_issues": len(findings),
                "configs_checked": len(configs),
                "source": "local_filesystem",
            },
        )
