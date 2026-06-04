"""
ZENIC-AGENTS — Auth Models (SQLite).

Tenant and User storage using SQLite.
Auto-creates the database and a default tenant + admin user on first use.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .auth import hash_password

# ── Database path ──────────────────────────────────────────────

DB_DIR = Path.home() / ".zenic_agents" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "auth.sqlite"

_lock = threading.Lock()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db() -> None:
    """Create tables if they don't exist. Idempotent."""
    with _lock:
        conn = _get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    plan TEXT NOT NULL DEFAULT 'free',
                    language TEXT NOT NULL DEFAULT 'es',
                    channel_prefs TEXT NOT NULL DEFAULT '{}',
                    max_clients INTEGER NOT NULL DEFAULT 1,
                    max_messages INTEGER NOT NULL DEFAULT 50,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'agent',
                    name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                );

                CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    date TEXT NOT NULL,
                    UNIQUE(tenant_id, metric, date),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                );

                CREATE INDEX IF NOT EXISTS idx_usage_tenant_date ON usage_tracking(tenant_id, date);
            """)
            conn.commit()
        finally:
            conn.close()


# ── Initialize DB at import time ───────────────────────────────

_init_db()


# ══════════════════════════════════════════════════════════════
# TENANT OPERATIONS
# ══════════════════════════════════════════════════════════════


def create_tenant(
    name: str,
    slug: str = "",
    plan: str = "free",
    language: str = "es",
    channel_prefs: dict | None = None,
) -> dict:
    """Create a new tenant. Returns tenant dict with id."""
    tenant_id = _new_id()
    now = _now_iso()
    slug = slug or name.lower().replace(" ", "-")
    channel_json = json.dumps(channel_prefs or {})

    plan_defaults = {
        "free": {"max_clients": 1, "max_messages": 50},
        "pro": {"max_clients": 50, "max_messages": 500},
        "enterprise": {"max_clients": 9999, "max_messages": 99999},
    }
    defaults = plan_defaults.get(plan, plan_defaults["free"])

    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO tenants
                   (id, name, slug, plan, language, channel_prefs,
                    max_clients, max_messages, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, name, slug, plan, language, channel_json,
                    defaults["max_clients"], defaults["max_messages"],
                    now, now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    return {
        "id": tenant_id,
        "name": name,
        "slug": slug,
        "plan": plan,
        "language": language,
        "channel_prefs": channel_prefs or {},
        "max_clients": defaults["max_clients"],
        "max_messages": defaults["max_messages"],
        "created_at": now,
        "updated_at": now,
    }


def get_tenant(tenant_id: str) -> dict | None:
    """Get a tenant by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_tenant(row)
    finally:
        conn.close()


def get_tenant_by_slug(slug: str) -> dict | None:
    """Get a tenant by slug."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tenants WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_tenant(row)
    finally:
        conn.close()


def list_tenants() -> list[dict]:
    """List all tenants."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM tenants ORDER BY created_at").fetchall()
        return [_row_to_tenant(r) for r in rows]
    finally:
        conn.close()


def _row_to_tenant(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["channel_prefs"] = json.loads(d.get("channel_prefs", "{}"))
    return d


# ══════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════


def create_user(
    email: str,
    password: str,
    tenant_id: str,
    role: str = "agent",
    name: str = "",
) -> dict:
    """Create a new user. Returns user dict (without password_hash)."""
    user_id = _new_id()
    now = _now_iso()
    pw_hash = hash_password(password)

    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO users
                   (id, tenant_id, email, password_hash, role, name, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, tenant_id, email.lower().strip(), pw_hash, role, name, now),
            )
            conn.commit()
        finally:
            conn.close()

    return {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": email.lower().strip(),
        "role": role,
        "name": name,
        "created_at": now,
    }


def get_user_by_email(email: str) -> dict | None:
    """Get a user by email (includes password_hash for verification)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    """Get a user by ID (without password_hash)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, tenant_id, email, role, name, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# AUTO-CREATE DEFAULT TENANT + ADMIN
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# USAGE TRACKING
# ══════════════════════════════════════════════════════════════


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_usage_today(tenant_id: str) -> dict[str, int]:
    """Get all usage counters for a tenant today."""
    today = _today_str()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT metric, count FROM usage_tracking WHERE tenant_id = ? AND date = ?",
            (tenant_id, today),
        ).fetchall()
        return {row["metric"]: row["count"] for row in rows}
    finally:
        conn.close()


def increment_usage(tenant_id: str, metric: str, amount: int = 1) -> None:
    """Increment a usage counter for a tenant today."""
    today = _today_str()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO usage_tracking (tenant_id, metric, count, date)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(tenant_id, metric, date)
                   DO UPDATE SET count = count + ?""",
                (tenant_id, metric, amount, today, amount),
            )
            conn.commit()
        finally:
            conn.close()


def count_clients_today(tenant_id: str) -> int:
    """Return how many clients were created by this tenant today."""
    return get_usage_today(tenant_id).get("clients_created", 0)


ALLOWED_TENANT_COLUMNS = frozenset({
    "name", "slug", "plan", "language", "channel_prefs",
    "max_clients", "max_messages",
})


def update_tenant(tenant_id: str, updates: dict) -> dict | None:
    """Update tenant fields (whitelisted columns only). Returns updated tenant or None."""
    tenant = get_tenant(tenant_id)
    if tenant is None:
        return None

    now = _now_iso()
    set_clauses = []
    values: list = []

    for key, val in updates.items():
        if key not in ALLOWED_TENANT_COLUMNS:
            continue  # Skip unknown columns (prevents SQL injection)
        if key == "channel_prefs":
            val = json.dumps(val)
        set_clauses.append(f"{key} = ?")
        values.append(val)

    if not set_clauses:
        return tenant

    values.append(now)
    values.append(tenant_id)

    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                f"UPDATE tenants SET {', '.join(set_clauses)}, updated_at = ? WHERE id = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()

    return get_tenant(tenant_id)


def _ensure_defaults() -> None:
    """Create a default tenant and admin user if none exist."""
    try:
        existing = list_tenants()
        if existing:
            return

        tenant = create_tenant(name="Default", slug="default", plan="enterprise")

        create_user(
            email="admin@zenic.ai",
            password="admin123",  # Change on first login!
            tenant_id=tenant["id"],
            role="admin",
            name="Admin",
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Could not create default tenant/admin: %s. "
            "Set ZENIC_AGENTS_JWT_SECRET and restart.", e
        )


_ensure_defaults()
