"""DuplicateRecordsMonitor — Detecta registros duplicados en la BD.

Peso: WARNING (2) — Datos corruptos/sucios.

Escanea tablas en la BD LOCAL buscando duplicados en campos clave.
NO espera a que el usuario note inconsistencias.
"""

from __future__ import annotations

import logging
from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight
from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class DuplicateRecordsMonitor(BaseMonitor):
    """Monitor de registros duplicados — escanea la BD del usuario."""

    name = "duplicate_records"
    weight = MonitorWeight.WARNING
    description = "Detecta registros duplicados en tablas de la BD local"
    interval_seconds = 7200  # Cada 2 horas

    # Tablas y columnas a verificar por duplicados
    DEFAULT_CHECKS: list[dict[str, Any]] = [
        {"table": "clientes", "columns": ["email", "telefono"]},
        {"table": "productos", "columns": ["codigo", "nombre"]},
        {"table": "facturas", "columns": ["numero"]},
    ]

    def __init__(self, scanner: LocalDataScanner, checks: list[dict] | None = None):
        super().__init__(scanner)
        self.checks = checks or self.DEFAULT_CHECKS

    def check(self) -> MonitorResult:
        """Busca registros duplicados en la BD del usuario."""
        all_findings = []

        for check_config in self.checks:
            table = check_config["table"]
            columns = check_config["columns"]

            if not self.scanner.db.table_exists(table):
                continue

            for col in columns:
                # Verificar si la columna existe
                schema = self.scanner.db.get_table_schema(table)
                col_names = [c["name"] for c in schema]
                if col not in col_names:
                    continue

                duplicates = self.scanner.scan_duplicates(table, [col])
                for dup in duplicates:
                    all_findings.append({
                        "type": "duplicate_record",
                        "table": table,
                        "column": col,
                        "value": dup.get(col, "?"),
                        "count": dup.get("duplicate_count", 2),
                        "message": f"Duplicado en {table}.{col}: '{dup.get(col, '?')}' aparece {dup.get('duplicate_count', 2)} veces",
                    })

        if not all_findings:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "No se encontraron registros duplicados", "tables_checked": len(self.checks)},
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=all_findings,
            healthy=False,
            details={
                "total_duplicates": len(all_findings),
                "tables_checked": len(self.checks),
                "source": "local_database",
            },
        )
