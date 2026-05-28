"""
ZENIC-AGENTS - Database Initializer v17 (FastPool Delegation)

Inicializa todas las bases de datos SQLite con:
- WAL mode para concurrencia sin locks
- PRAGMA optimizados para ARM (menos memoria, mas eficiencia)
- Indice en theorem_cache para skeleton_hash lookups rapidos

.. deprecated:: FASE 1.3
   The connection pool functions (get_connection, write_lock, close_all_connections)
   now delegate to FastPool (src.core.shared.fast_connection_pool) internally.
   Only initialize_databases() and utility functions (get_data_dir, get_db_path)
   should continue to be used for table creation.

   Migration guide (for new code):
   - get_connection(db) → fast_pool().get(db)
   - write_lock(db) → fast_pool().write(db)
   - close_all_connections() → close_all_pools()

   Existing code that uses get_connection() / write_lock() continues to work
   through transparent FastPool delegation — no changes needed in consumers.
"""

import atexit
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "close_all_connections",
    "get_connection",
    "get_data_dir",
    "get_db_path",
    "get_encrypted_connection",
    "get_projects_dir",
    "initialize_databases",
    "is_encryption_enabled",
    "write_lock",
]

# Environment variable for enabling SQLCipher encryption on all connections
_ZENIC_DB_PASSPHRASE_ENV = "ZENIC_DB_PASSPHRASE"  # noqa: S105

# Track whether the old pool is still needed (for backward compat during migration)
_legacy_connections: dict[str, sqlite3.Connection] = {}
_legacy_lock = threading.Lock()


def _get_fast_pool():
    """Get the FastPool singleton, with fallback if import fails."""
    try:
        from src.core.shared.fast_connection_pool import fast_pool
        return fast_pool()
    except ImportError:
        logger.warning("db_initializer: FastPool not available, using legacy connection management")
        return None


def _optimize_pragma(conn: sqlite3.Connection) -> None:
    """Aplica PRAGMA optimizados para rendimiento en ARM.

    WAL mode: Permite lecturas concurrentes sin bloquear escrituras.
    cache_size: -8192 = 8MB cache (doubled from 4MB)
    synchronous NORMAL: Mas rapido que FULL, seguro con WAL
    temp_store MEMORY: Tablas temporales en RAM
    mmap_size: Memory-mapped I/O para lecturas grandes
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-8192")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=67108864")
    conn.execute("PRAGMA wal_autocheckpoint=1000")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")


def is_encryption_enabled() -> bool:
    """Check whether SQLCipher encryption is available and a passphrase is set.

    Returns True only when BOTH conditions are met:
      1. A SQLCipher library (pysqlcipher3 or sqlcipher3) is importable
      2. The ``ZENIC_DB_PASSPHRASE`` environment variable is non-empty

    When this returns True, ``get_connection()`` will automatically use
    SQLCipher for all new connections.
    """
    try:
        from src.core.shared.sqlcipher_helper import HAS_SQLCIPHER
        return HAS_SQLCIPHER and bool(os.environ.get(_ZENIC_DB_PASSPHRASE_ENV, ""))
    except ImportError:
        return False


def get_data_dir() -> Path:
    """Get the data directory path, creating it if needed.

    Supports Android/Termux environments via ANDROID_ARGUMENT env var.
    Default: ``~/.zenic_agents/data``
    """
    if "ANDROID_ARGUMENT" in os.environ:
        try:
            from android.storage import app_storage_path  # type: ignore[import-unresolved]
            data_dir = Path(app_storage_path()) / "zenic_data"
        except Exception:
            data_dir = Path.home() / ".zenic_agents" / "data"
    else:
        data_dir = Path.home() / ".zenic_agents" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path(db_name: str) -> str:
    """Get the full path for a database file in the data directory."""
    return str(get_data_dir() / db_name)


def get_projects_dir() -> Path:
    """Get the projects directory, creating it if needed."""
    p = get_data_dir() / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_encrypted_connection(
    db_name: str,
    passphrase: str = "",
) -> sqlite3.Connection:
    """Create an encrypted database connection using SQLCipher.

    When SQLCipher is available and a non-empty passphrase is provided,
    returns an AES-256 encrypted connection.  Otherwise falls back to
    plain SQLite with a warning log.

    Args:
        db_name: Database filename (e.g. ``"graph_ast.sqlite"``).
        passphrase: Encryption key.  If empty and the env-var
            ``ZENIC_DB_PASSPHRASE`` is set, that value is used instead.

    Returns:
        An open ``sqlite3.Connection`` (encrypted or plain).
    """
    try:
        from src.core.shared.sqlcipher_helper import get_sqlcipher_connection
        has_sqlcipher = True
    except ImportError:
        has_sqlcipher = False

    effective_passphrase = passphrase or os.environ.get(_ZENIC_DB_PASSPHRASE_ENV, "")
    path = get_db_path(db_name)

    if effective_passphrase and has_sqlcipher:
        conn = get_sqlcipher_connection(
            path,
            effective_passphrase,
            kdf_iterations=64000,
            cipher_page_size=4096,
            apply_pragmas=False,
        )
        _optimize_pragma(conn)
        conn.row_factory = sqlite3.Row
        logger.info("get_encrypted_connection: SQLCipher AES-256 for '%s'", db_name)
        return conn

    # Fallback: plain SQLite (no passphrase provided or no SQLCipher)
    conn = sqlite3.connect(path, check_same_thread=False)
    _optimize_pragma(conn)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection(db_name: str) -> sqlite3.Connection:
    """Get a database connection, delegating to FastPool when available.

    .. deprecated:: FASE 1.3
       Use ``fast_pool().get(db_name)`` instead for better thread-local caching,
       3-layer connection management, and reduced SQLITE_BUSY contention.

       This function now delegates to FastPool transparently.
       Existing consumers continue to work without code changes.

    When FastPool is unavailable (e.g., during early startup or in
    constrained environments), falls back to direct SQLite connection
    with PRAGMA optimization.

    When ``is_encryption_enabled()`` is True, the connection will
    use SQLCipher encryption automatically.

    Args:
        db_name: Database filename (e.g. ``"graph_ast.sqlite"``).

    Returns:
        A ``sqlite3.Connection`` from the pool.
    """
    import warnings

    warnings.warn(
        "db_initializer.get_connection() is deprecated since FASE 1.3. "
        "Use fast_pool().get(db_name) instead for better connection management.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Delegate to FastPool when available
    pool = _get_fast_pool()
    if pool is not None:
        try:
            return pool.get(db_name)
        except Exception as exc:
            logger.warning(
                "db_initializer: FastPool.get() failed for '%s', "
                "falling back to direct connection: %s",
                db_name, exc,
            )

    # Fallback: direct connection (FastPool unavailable)
    if is_encryption_enabled():
        return get_encrypted_connection(db_name)

    path = get_db_path(db_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with _legacy_lock:
        if db_name in _legacy_connections:
            conn = _legacy_connections[db_name]
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                del _legacy_connections[db_name]

        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _optimize_pragma(conn)
        _legacy_connections[db_name] = conn
        return conn


def close_all_connections() -> None:
    """Close all database connections (both FastPool and legacy).

    Delegates to FastPool's close_all() when available, and also
    closes any legacy connections that may have been created before
    FastPool was available.
    """
    # Close FastPool connections
    try:
        from src.core.shared.fast_connection_pool import close_all_pools
        close_all_pools()
    except ImportError:
        pass

    # Close any legacy connections
    with _legacy_lock:
        for key, conn in list(_legacy_connections.items()):
            try:
                conn.close()
            except Exception as exc:
                logger.debug("close_all_connections: Failed to close '%s': %s", key, exc)
        _legacy_connections.clear()


# Register cleanup on process exit to prevent leaked DB connections
atexit.register(close_all_connections)


class write_lock:
    """Context manager to acquire the per-database write lock.

    .. deprecated:: FASE 1.3
       Use ``fast_pool().write(db_name)`` instead for automatic
       commit/rollback handling with per-DB write locks.

    When FastPool is available, delegates to ``fast_pool().write()``.
    Otherwise, falls back to a simple threading.Lock per database.

    Usage::

        conn = get_connection("graph_ast.sqlite")
        with write_lock("graph_ast.sqlite"):
            conn.execute("INSERT INTO ...")
            conn.commit()

    This ensures that only one thread writes to a given database at a time,
    preventing 'database is locked' errors and data corruption.
    """

    def __init__(self, db_name: str) -> None:
        self._db_name = db_name
        self._pool_ctx: Any = None
        self._fallback_lock: threading.Lock | None = None

    def __enter__(self) -> "write_lock":
        # Try FastPool delegation first
        pool = _get_fast_pool()
        if pool is not None:
            try:
                self._pool_ctx = pool.write(self._db_name)
                self._pool_ctx.__enter__()
                return self
            except Exception as exc:
                logger.debug(
                    "write_lock: FastPool.write() failed for '%s', "
                    "using fallback lock: %s",
                    self._db_name, exc,
                )

        # Fallback: simple per-DB lock
        with _legacy_lock:
            # Reuse lock from legacy connection if available
            if self._db_name not in _write_locks_fallback:
                _write_locks_fallback[self._db_name] = threading.Lock()
            self._fallback_lock = _write_locks_fallback[self._db_name]

        if self._fallback_lock is not None:
            self._fallback_lock.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self._pool_ctx is not None:
            self._pool_ctx.__exit__(exc_type, exc_val, exc_tb)
            self._pool_ctx = None
        elif self._fallback_lock is not None:
            self._fallback_lock.release()
            self._fallback_lock = None
        return False


# Fallback write locks for when FastPool is unavailable
_write_locks_fallback: dict[str, threading.Lock] = {}


def _ensure_table(
    conn: sqlite3.Connection,
    schema: str,
    indexes: list[str] | None = None,
) -> None:
    """Create a table with its indexes in a single transaction."""
    conn.execute(schema)
    for idx in (indexes or []):
        conn.execute(idx)
    conn.commit()


def initialize_databases() -> None:
    """Create all SQLite tables with complete schemas v17 + indexes + PRAGMA.

    Uses FastPool for connections when available, falling back to
    get_connection() otherwise. This ensures tables are created
    regardless of which pool is active.
    """
    # Use FastPool directly to avoid deprecation warnings during init
    pool = _get_fast_pool()
    _get_conn = pool.get if pool else get_connection

    # Graph AST (Phase 2: tenant-aware)
    conn = _get_conn("graph_ast.sqlite")
    _ensure_table(conn, """CREATE TABLE IF NOT EXISTS ast_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        node_type TEXT NOT NULL,
        name TEXT NOT NULL,
        start_byte INTEGER NOT NULL,
        end_byte INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        docstring TEXT,
        complexity INTEGER DEFAULT 1,
        connections TEXT DEFAULT '[]',
        tenant_id TEXT NOT NULL DEFAULT '__anonymous__',
        UNIQUE(file_path, name, node_type, tenant_id))""", [
        "CREATE INDEX IF NOT EXISTS idx_ast_name ON ast_nodes(name)",
        "CREATE INDEX IF NOT EXISTS idx_ast_type ON ast_nodes(node_type)",
        "CREATE INDEX IF NOT EXISTS idx_ast_tenant ON ast_nodes(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_ast_tenant_file ON ast_nodes(tenant_id, file_path)",
    ])

    # Theorem Cache
    conn = _get_conn("theorem_cache.sqlite")
    _ensure_table(conn, """CREATE TABLE IF NOT EXISTS theorems (
        structural_hash TEXT NOT NULL,
        operation TEXT NOT NULL,
        goal TEXT NOT NULL,
        proof_result TEXT NOT NULL,
        solution_payload TEXT,
        skeleton_hash TEXT,
        hit_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tenant_id TEXT NOT NULL DEFAULT '__anonymous__',
        PRIMARY KEY (structural_hash, tenant_id))""", [
        "CREATE INDEX IF NOT EXISTS idx_skeleton ON theorems(skeleton_hash)",
        "CREATE INDEX IF NOT EXISTS idx_theorems_tenant ON theorems(tenant_id)",
    ])

    # Merkle Ledger
    conn = _get_conn("merkle_ledger.sqlite")
    _ensure_table(conn, """CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        hash_sha256 TEXT NOT NULL,
        parent_hash TEXT NOT NULL,
        operation TEXT NOT NULL,
        timestamp REAL NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT '__anonymous__')""", [
        "CREATE INDEX IF NOT EXISTS idx_ledger_file ON ledger(file_path)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_tenant ON ledger(tenant_id)",
    ])

    # Request Log (Phase 2: tenant-aware)
    conn = _get_conn("request_log.sqlite")
    _ensure_table(conn, """CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        model TEXT,
        operation TEXT,
        goal TEXT,
        route TEXT,
        status TEXT,
        processing_time_ms INTEGER,
        solver_status TEXT,
        mcts_simulations INTEGER DEFAULT 0,
        cache_hit INTEGER DEFAULT 0,
        tenant_id TEXT NOT NULL DEFAULT '__anonymous__',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""", [
        "CREATE INDEX IF NOT EXISTS idx_requests_time ON requests(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_requests_tenant ON requests(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_requests_tenant_time ON requests(tenant_id, created_at)",
    ])

    logger.info("Databases initialized with WAL mode + PRAGMA optimizations (via %s)",
                "FastPool" if pool else "legacy pool")
