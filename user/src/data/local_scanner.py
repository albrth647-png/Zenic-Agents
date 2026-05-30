"""LocalDataScanner — El ojo del sistema proactivo sobre los datos LOCALES.

Este es el componente CLAVE que resuelve el problema del "adivino":
- El sistema NO necesita que el usuario reporte problemas por canales
- El sistema VE directamente en la base de datos y filesystem del usuario
- Detecta problemas ANTES de que el usuario se dé cuenta

Flujo:
    LocalDataScanner → SNA Monitors → AlertManager → ProactiveChannelBridge → Canal del usuario

Sin LocalDataScanner, el sistema proactivo es ciego:
    Solo ve canales → No puede detectar stock bajo, facturas vencidas, disk lleno, etc.

Con LocalDataScanner, el sistema proactivo VE todo:
    Escanea SQLite + filesystem → Detecta anomalías → Alerta al usuario por su canal
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.data.db_access import DBAccess
from src.data.fs_scanner import FileSystemScanner

logger = logging.getLogger(__name__)


class LocalDataScanner:
    """Fachada que unifica escaneo de base de datos y filesystem.

    Es el punto de entrada único para que los SNA monitors
    consulten datos locales sin acoplarse a la implementación.
    """

    def __init__(
        self,
        db_path: str | None = None,
        base_path: str | None = None,
    ):
        self.db = DBAccess(db_path)
        self.fs = FileSystemScanner(base_path)
        self._scan_cache: dict[str, Any] = {}
        self._cache_timestamp: datetime | None = None
        logger.info("LocalDataScanner inicializado — ojos sobre datos locales")

    # ------------------------------------------------------------------ #
    #  Escaneo de base de datos                                          #
    # ------------------------------------------------------------------ #

    def scan_database_schema(self) -> dict[str, Any]:
        """Escanea el esquema completo de la base de datos."""
        try:
            tables = self.db.list_tables()
            if not tables:
                return {"status": "empty", "tables": [], "message": "Base de datos vacía o no existe"}

            stats = self.db.get_all_table_stats()
            integrity = self.db.check_integrity()
            db_size = self.db.get_db_size_bytes()

            return {
                "status": "ok",
                "table_count": len(tables),
                "tables": stats,
                "integrity": integrity,
                "db_size_bytes": db_size,
                "db_size_mb": round(db_size / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.error(f"Error escaneando esquema de BD: {e}")
            return {"status": "error", "error": str(e)}

    def scan_low_stock(self, threshold: int = 5) -> list[dict[str, Any]]:
        """Busca productos con stock bajo en la BD del usuario."""
        return self.db.get_low_stock_items(threshold=threshold)

    def scan_overdue_invoices(self) -> list[dict[str, Any]]:
        """Busca facturas vencidas en la BD del usuario."""
        return self.db.get_overdue_invoices()

    def scan_tomorrow_appointments(self) -> list[dict[str, Any]]:
        """Busca citas de mañana en la BD del usuario."""
        return self.db.get_tomorrow_appointments()

    def scan_unpaid_balances(self) -> list[dict[str, Any]]:
        """Busca saldos pendientes en la BD del usuario."""
        return self.db.get_unpaid_balances()

    def scan_stale_inventory(self, days: int = 90) -> list[dict[str, Any]]:
        """Busca inventario estancado en la BD del usuario."""
        return self.db.get_stale_inventory(days=days)

    def scan_sales_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """Obtiene tendencia de ventas de la BD del usuario."""
        return self.db.get_sales_trend(days=days)

    def scan_orphan_records(
        self, child_table: str, child_fk: str, parent_table: str, parent_pk: str = "id"
    ) -> list[dict[str, Any]]:
        """Busca registros huérfanos en la BD del usuario."""
        if not self.db.table_exists(child_table) or not self.db.table_exists(parent_table):
            return []
        return self.db.find_orphan_records(child_table, child_fk, parent_table, parent_pk)

    def scan_duplicates(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        """Busca registros duplicados en la BD del usuario."""
        if not self.db.table_exists(table):
            return []
        return self.db.find_duplicates(table, columns)

    def scan_null_required_fields(self, table: str, required_columns: list[str]) -> list[dict[str, Any]]:
        """Busca campos requeridos vacíos en la BD del usuario."""
        if not self.db.table_exists(table):
            return []
        return self.db.find_null_fields(table, required_columns)

    # ------------------------------------------------------------------ #
    #  Escaneo de filesystem                                             #
    # ------------------------------------------------------------------ #

    def scan_disk_space(self) -> dict[str, Any]:
        """Verifica espacio en disco del usuario."""
        return self.fs.get_disk_usage()

    def scan_config_health(self) -> list[dict[str, Any]]:
        """Verifica salud de archivos de configuración."""
        return self.fs.scan_config_files()

    def scan_backup_status(self) -> dict[str, Any]:
        """Verifica estado de backups del usuario."""
        return self.fs.scan_backups()

    def scan_log_health(self) -> dict[str, Any]:
        """Verifica salud de archivos de log."""
        return self.fs.scan_logs()

    def scan_data_dirs(self) -> list[dict[str, Any]]:
        """Verifica directorios de datos."""
        return self.fs.scan_data_directories()

    def scan_temp_cleanup(self) -> dict[str, Any]:
        """Verifica archivos temporales que necesitan limpieza."""
        return self.fs.scan_temp_files()

    # ------------------------------------------------------------------ #
    #  Escaneo completo                                                  #
    # ------------------------------------------------------------------ #

    def full_scan(self) -> dict[str, Any]:
        """Ejecuta un escaneo completo de todos los datos locales.

        Este es el método que el SNA Scheduler llama periódicamente.
        Los monitores individuales usan métodos específicos.
        """
        logger.info("Iniciando escaneo completo de datos locales...")

        scan_results: dict[str, Any] = {
            "database": self.scan_database_schema(),
            "disk": self.scan_disk_space(),
            "configs": self.scan_config_health(),
            "backups": self.scan_backup_status(),
            "logs": self.scan_log_health(),
            "data_dirs": self.scan_data_dirs(),
            "temp_files": self.scan_temp_cleanup(),
            "business_data": {
                "low_stock": self.scan_low_stock(),
                "overdue_invoices": self.scan_overdue_invoices(),
                "tomorrow_appointments": self.scan_tomorrow_appointments(),
                "unpaid_balances": self.scan_unpaid_balances(),
                "stale_inventory": self.scan_stale_inventory(),
                "sales_trend": self.scan_sales_trend(),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Cachear resultados
        self._scan_cache = scan_results
        self._cache_timestamp = datetime.now()

        # Contar problemas encontrados
        issues = 0
        bd = scan_results.get("business_data", {})
        issues += len(bd.get("low_stock", []))
        issues += len(bd.get("overdue_invoices", []))
        issues += len(bd.get("unpaid_balances", []))
        issues += len(bd.get("stale_inventory", []))

        disk = scan_results.get("disk", {})
        if disk.get("status") in ("warning", "critical"):
            issues += 1

        logger.info(f"Escaneo completo finalizado — {issues} problemas detectados")
        return scan_results

    def get_cached_scan(self, max_age_seconds: int = 300) -> dict[str, Any] | None:
        """Obtiene el último escaneo si no es muy viejo."""
        if self._cache_timestamp is None:
            return None

        age = (datetime.now() - self._cache_timestamp).total_seconds()
        if age > max_age_seconds:
            return None

        return self._scan_cache

    def close(self):
        """Cierra conexiones."""
        self.db.close()
        logger.info("LocalDataScanner cerrado")

    def __repr__(self) -> str:
        return f"LocalDataScanner(db={self.db.db_path})"
