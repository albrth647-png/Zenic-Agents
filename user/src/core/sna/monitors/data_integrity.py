"""DataIntegrityMonitor — Detecta problemas de integridad en la BD.

Peso: CRITICAL (3) — Datos corruptos = decisiones erróneas.

Escanea la BD LOCAL del usuario verificando:
- PRAGMA integrity_check
- Registros huérfanos (FK sin padre)
- Campos requeridos NULL
NO espera a que una query devuelva resultados inesperados.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

if TYPE_CHECKING:
    from src.data.local_scanner import LocalDataScanner

logger = logging.getLogger(__name__)


class DataIntegrityMonitor(BaseMonitor):
    """Monitor de integridad de datos — escanea la BD del usuario."""

    name = "data_integrity"
    weight = MonitorWeight.CRITICAL
    description = "Detecta problemas de integridad en la BD local (huérfanos, NULLs, corruptos)"
    interval_seconds = 3600  # Cada hora

    # Relaciones FK a verificar (child_table, child_fk, parent_table)
    DEFAULT_FK_CHECKS: list[dict[str, str]] = [  # noqa: RUF012
        {"child": "facturas", "fk": "cliente_id", "parent": "clientes"},
        {"child": "detalles_factura", "fk": "factura_id", "parent": "facturas"},
        {"child": "detalles_factura", "fk": "producto_id", "parent": "productos"},
    ]

    # Tablas con campos requeridos
    DEFAULT_NULL_CHECKS: list[dict[str, Any]] = [  # noqa: RUF012
        {"table": "clientes", "required": ["nombre", "email"]},
        {"table": "productos", "required": ["nombre", "precio"]},
        {"table": "facturas", "required": ["cliente_id", "fecha", "monto"]},
    ]

    def __init__(
        self, scanner: LocalDataScanner, fk_checks: list[dict] | None = None, null_checks: list[dict] | None = None
    ):
        super().__init__(scanner)
        self.fk_checks = fk_checks or self.DEFAULT_FK_CHECKS
        self.null_checks = null_checks or self.DEFAULT_NULL_CHECKS

    def check(self) -> MonitorResult:
        """Verifica integridad de datos en la BD del usuario."""
        findings = []

        # 1. PRAGMA integrity_check
        integrity = self.scanner.db.check_integrity()
        if integrity.get("status") != "ok":
            findings.append(
                {
                    "type": "database_corrupt",
                    "message": f"Integridad de BD: {integrity.get('status', 'unknown')}",
                }
            )

        # 2. Registros huérfanos
        for fk_check in self.fk_checks:
            child = fk_check["child"]
            fk = fk_check["fk"]
            parent = fk_check["parent"]

            if not self.scanner.db.table_exists(child) or not self.scanner.db.table_exists(parent):
                continue

            orphans = self.scanner.scan_orphan_records(child, fk, parent)
            if orphans:
                findings.append(
                    {
                        "type": "orphan_records",
                        "child_table": child,
                        "fk_column": fk,
                        "parent_table": parent,
                        "count": len(orphans),
                        "message": f"{len(orphans)} registros huérfanos en {child}.{fk} → {parent}",
                    }
                )

        # 3. Campos requeridos NULL
        for null_check in self.null_checks:
            table = null_check["table"]
            required = null_check["required"]

            if not self.scanner.db.table_exists(table):
                continue

            # Verificar qué columnas existen realmente
            schema = self.scanner.db.get_table_schema(table)
            existing_cols = {c["name"] for c in schema}
            check_cols = [c for c in required if c in existing_cols]

            if not check_cols:
                continue

            nulls = self.scanner.scan_null_required_fields(table, check_cols)
            if nulls:
                findings.append(
                    {
                        "type": "null_required_fields",
                        "table": table,
                        "columns": check_cols,
                        "count": len(nulls),
                        "message": f"{len(nulls)} registros en {table} con campos requeridos vacíos ({', '.join(check_cols)})",
                    }
                )

        if not findings:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "Integridad de datos correcta"},
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_issues": len(findings),
                "source": "local_database",
            },
        )
