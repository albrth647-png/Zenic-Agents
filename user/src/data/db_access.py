"""DBAccess — Capa de acceso directo a la base SQLite del usuario.

No usa ORM. SQL directo para máximo control y transparencia.
Cada query es explícita, cada resultado es verificable.

El SNA NO es adivino: pregunta directamente a los datos del usuario.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class DBAccess:
    """Acceso directo a la base de datos SQLite del usuario.

    Lee el DATABASE_URL del entorno y proporciona métodos
    para consultar tablas, registros y esquemas.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or self._resolve_db_path()
        self._conn: sqlite3.Connection | None = None
        logger.info(f"DBAccess inicializado → {self.db_path}")

    # ------------------------------------------------------------------ #
    #  Inicialización                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_db_path() -> str:
        """Resuelve la ruta a la base de datos del usuario.

        Orden de prioridad:
        1. DATABASE_URL en entorno (formato file:/path/to/db)
        2. DATABASE_PATH en entorno
        3. Default: ~/.zenic_agents/data/custom.db (portable, no hardcodeado)
        """
        url = os.environ.get("DATABASE_URL", "")
        if url.startswith("file:"):
            return url[5:]

        path = os.environ.get("DATABASE_PATH", "")
        if path:
            return path

        # Ruta portable basada en el home del usuario (no hardcodeada)
        default = os.path.join(os.path.expanduser("~"), ".zenic_agents", "data", "custom.db")
        os.makedirs(os.path.dirname(default), exist_ok=True)
        return default

    def _get_conn(self) -> sqlite3.Connection:
        """Obtiene conexión SQLite (lazy, reutilizable)."""
        if self._conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        """Cierra la conexión."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ #
    #  Consultas de esquema                                              #
    # ------------------------------------------------------------------ #

    def list_tables(self) -> list[str]:
        """Lista todas las tablas de usuario en la base de datos."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """Obtiene el esquema de una tabla (columnas, tipos, nullable)."""
        conn = self._get_conn()
        rows = conn.execute(f"PRAGMA table_info([{table_name}])").fetchall()
        return [
            {
                "cid": r["cid"],
                "name": r["name"],
                "type": r["type"],
                "notnull": bool(r["notnull"]),
                "default": r["dflt_value"],
                "pk": bool(r["pk"]),
            }
            for r in rows
        ]

    def get_table_count(self, table_name: str) -> int:
        """Cuenta los registros en una tabla."""
        conn = self._get_conn()
        row = conn.execute(f"SELECT COUNT(*) as cnt FROM [{table_name}]").fetchone()  # noqa: S608
        return row["cnt"] if row else 0

    def get_foreign_keys(self, table_name: str) -> list[dict[str, Any]]:
        """Obtiene las foreign keys de una tabla."""
        conn = self._get_conn()
        rows = conn.execute(f"PRAGMA foreign_key_list([{table_name}])").fetchall()
        return [dict(r) for r in rows]

    def get_indexes(self, table_name: str) -> list[dict[str, Any]]:
        """Obtiene los índices de una tabla."""
        conn = self._get_conn()
        rows = conn.execute(f"PRAGMA index_list([{table_name}])").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Consultas de datos                                                #
    # ------------------------------------------------------------------ #

    def execute_query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Ejecuta una query SELECT y devuelve resultados como dicts.

        SOLO para SELECT. No permite INSERT/UPDATE/DELETE.
        """
        sql_stripped = sql.strip().upper()
        if not sql_stripped.startswith("SELECT") and not sql_stripped.startswith("PRAGMA"):
            raise ValueError(f"DBAccess.execute_query solo permite SELECT/PRAGMA, no: {sql_stripped[:20]}")

        conn = self._get_conn()
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Ejecuta una query INSERT/UPDATE/DELETE. Devuelve rows affected.

        Solo para uso interno del Autopilot/SNA. Requiere aprobación del SafetyGate.
        """
        conn = self._get_conn()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount

    # ------------------------------------------------------------------ #
    #  Consultas de integridad                                           #
    # ------------------------------------------------------------------ #

    def check_integrity(self) -> dict[str, Any]:
        """Ejecuta PRAGMA integrity_check en toda la base de datos."""
        conn = self._get_conn()
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return {"status": dict(row).get("integrity_check", "unknown") if row else "no_result"}

    def find_orphan_records(
        self, child_table: str, child_fk: str, parent_table: str, parent_pk: str = "id"
    ) -> list[dict[str, Any]]:
        """Busca registros huérfanos (child con FK sin padre)."""
        sql = f"""  # noqa: S608
            SELECT c.* FROM [{child_table}] c
            LEFT JOIN [{parent_table}] p ON c.[{child_fk}] = p.[{parent_pk}]
            WHERE p.[{parent_pk}] IS NULL AND c.[{child_fk}] IS NOT NULL
        """  # noqa: S608
        return self.execute_query(sql)

    def find_duplicates(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        """Busca registros duplicados basado en columnas específicas."""
        cols = ", ".join(f"[{c}]" for c in columns)
        sql = f"""  # noqa: S608
            SELECT {cols}, COUNT(*) as duplicate_count
            FROM [{table}]
            GROUP BY {cols}
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
        """  # noqa: S608
        return self.execute_query(sql)

    def find_null_fields(self, table: str, required_columns: list[str]) -> list[dict[str, Any]]:
        """Busca registros con campos requeridos que son NULL."""
        conditions = " OR ".join(f"[{c}] IS NULL" for c in required_columns)
        sql = f"SELECT * FROM [{table}] WHERE {conditions}"  # noqa: S608
        return self.execute_query(sql)

    # ------------------------------------------------------------------ #
    #  Consultas de negocio (genéricas pero comunes)                     #
    # ------------------------------------------------------------------ #

    def get_low_stock_items(
        self, stock_column: str = "stock", threshold: int = 5, table: str = "productos"
    ) -> list[dict[str, Any]]:
        """Busca productos con stock bajo."""
        try:
            return self.execute_query(
                f"SELECT * FROM [{table}] WHERE [{stock_column}] <= ? ORDER BY [{stock_column}] ASC",  # noqa: S608
                (threshold,),
            )
        except Exception:
            return []

    def get_overdue_invoices(
        self,
        table: str = "facturas",
        due_column: str = "fecha_vencimiento",
        status_column: str = "estado",
        paid_status: str = "pagada",
    ) -> list[dict[str, Any]]:
        """Busca facturas vencidas sin pagar."""
        try:
            return self.execute_query(
                f"SELECT * FROM [{table}] WHERE [{status_column}] != ? AND [{due_column}] < date('now') ORDER BY [{due_column}] ASC",  # noqa: S608
                (paid_status,),
            )
        except Exception:
            return []

    def get_tomorrow_appointments(self, table: str = "citas", date_column: str = "fecha") -> list[dict[str, Any]]:
        """Busca citas programadas para mañana."""
        try:
            return self.execute_query(
                f"SELECT * FROM [{table}] WHERE [{date_column}] = date('now', '+1 day') ORDER BY [{date_column}] ASC"  # noqa: S608
            )
        except Exception:
            return []

    def get_unpaid_balances(
        self, table: str = "clientes", balance_column: str = "saldo_pendiente", threshold: float = 0
    ) -> list[dict[str, Any]]:
        """Busca clientes con saldo pendiente."""
        try:
            return self.execute_query(
                f"SELECT * FROM [{table}] WHERE [{balance_column}] > ? ORDER BY [{balance_column}] DESC",  # noqa: S608
                (threshold,),
            )
        except Exception:
            return []

    def get_sales_trend(
        self, table: str = "ventas", date_column: str = "fecha", amount_column: str = "monto", days: int = 30
    ) -> list[dict[str, Any]]:
        """Obtiene tendencia de ventas de los últimos N días.

        El parámetro ``days`` se pasa como argumento parametrizado (?)
        para evitar inyección SQL. Los nombres de tabla y columnas
        siguen usando f-string porque son identificadores de esquema,
        no valores de datos.
        """
        try:
            # Validar que days sea un entero positivo (defensa en profundidad)
            if not isinstance(days, int) or days < 0:
                logger.warning("get_sales_trend: days=%r no es un entero positivo, usando 30", days)
                days = 30
            return self.execute_query(
                f"SELECT date([{date_column}]) as dia, SUM([{amount_column}]) as total "  # noqa: S608
                f"FROM [{table}] WHERE [{date_column}] >= date('now', ? || ' days') "
                f"GROUP BY date([{date_column}]) ORDER BY dia ASC",
                (f"-{days}",),
            )
        except Exception:
            return []

    def get_stale_inventory(
        self, table: str = "productos", last_sold_column: str = "ultima_venta", days: int = 90
    ) -> list[dict[str, Any]]:
        """Busca productos sin venta en los últimos N días.

        El parámetro ``days`` se pasa como argumento parametrizado (?)
        para evitar inyección SQL. Los nombres de tabla y columnas
        siguen usando f-string porque son identificadores de esquema,
        no valores de datos.
        """
        try:
            # Validar que days sea un entero positivo (defensa en profundidad)
            if not isinstance(days, int) or days < 0:
                logger.warning("get_stale_inventory: days=%r no es un entero positivo, usando 90", days)
                days = 90
            return self.execute_query(
                f"SELECT * FROM [{table}] WHERE [{last_sold_column}] < date('now', ? || ' days') "  # noqa: S608
                f"OR [{last_sold_column}] IS NULL",
                (f"-{days}",),
            )
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  Utilidades                                                        #
    # ------------------------------------------------------------------ #

    def get_all_table_stats(self) -> dict[str, dict[str, Any]]:
        """Obtiene estadísticas de todas las tablas (conteo, tamaño)."""
        tables = self.list_tables()
        stats = {}
        for table in tables:
            count = self.get_table_count(table)
            schema = self.get_table_schema(table)
            fks = self.get_foreign_keys(table)
            stats[table] = {
                "row_count": count,
                "columns": len(schema),
                "foreign_keys": len(fks),
                "schema": schema,
            }
        return stats

    def table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe."""
        return table_name in self.list_tables()

    def get_db_size_bytes(self) -> int:
        """Tamaño del archivo de base de datos en bytes."""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0

    def __repr__(self) -> str:
        return f"DBAccess({self.db_path})"
