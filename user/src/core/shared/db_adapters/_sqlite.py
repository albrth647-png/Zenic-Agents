"""
ZENIC-AGENTS v16 - SQLite Database Adapter

Default adapter for development and Termux. Uses aiosqlite for async
operations. Maintains backward compatibility with db_initializer.py.
"""

import logging
from typing import Any

from ._base import DatabaseBackend

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseBackend):
    """SQLite adapter — default for development and Termux.

    Uses aiosqlite for async operations. Maintains backward compatibility
    with the existing db_initializer.py connection pool.
    """

    backend_name = "sqlite"

    def __init__(self, db_path: str = "") -> None:
        self._db_path = db_path
        self._pool: Any | None = None

    async def initialize(self) -> None:
        """Initialize using the existing db_initializer for backward compat."""
        from src.core.shared.db_initializer import initialize_databases
        initialize_databases()
        logger.info("SQLiteDatabase: initialized with WAL mode + PRAGMA optimizations")

    async def close(self) -> None:
        from src.core.shared.db_initializer import close_all_connections
        close_all_connections()
        logger.info("SQLiteDatabase: all connections closed")

    async def connection(self) -> Any:
        """Return a synchronous SQLite connection wrapped for async compat.

        For SQLite, we use the existing connection pool from db_initializer.
        The connection is NOT async — callers should use run_in_executor
        for blocking operations, or use the sync API directly.
        """
        from src.core.shared.db_initializer import get_connection
        return get_connection(self._db_path or "graph_ast.sqlite")

    async def execute(self, conn: Any, query: str, params: tuple | None = None) -> None:
        if params:
            conn.execute(query, params)  # nosemgrep: sqlalchemy-execute-raw-query
        else:
            conn.execute(query)  # nosemgrep: sqlalchemy-execute-raw-query
        conn.commit()

    async def fetch_one(self, conn: Any, query: str, params: tuple | None = None) -> dict[str, Any] | None:
        cursor = conn.execute(query, params) if params else conn.execute(query)  # nosemgrep: sqlalchemy-execute-raw-query
        row = cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, 'keys'):
            return dict(zip(row.keys(), row, strict=False))
        return dict(row) if row else None

    async def fetch_all(self, conn: Any, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        cursor = conn.execute(query, params) if params else conn.execute(query)  # nosemgrep: sqlalchemy-execute-raw-query
        rows = cursor.fetchall()
        if rows and hasattr(rows[0], 'keys'):
            return [dict(zip(r.keys(), r, strict=False)) for r in rows]
        return [dict(r) for r in rows]

    async def fetch_val(self, conn: Any, query: str, params: tuple | None = None) -> Any:
        cursor = conn.execute(query, params) if params else conn.execute(query)  # nosemgrep: sqlalchemy-execute-raw-query
        row = cursor.fetchone()
        return row[0] if row else None

    def format_param(self, index: int) -> str:
        return "?"
