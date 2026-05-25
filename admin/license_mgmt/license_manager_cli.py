"""
Zenic-Agents — License Management CLI (Admin)

Admin tool for creating, listing, revoking, and auditing licenses.
Uses the key generator from admin/keygen/ and provides a full
license lifecycle management interface.

Features:
  - Create single/bulk licenses with tier assignment
  - List all issued licenses
  - Revoke a license (kill switch)
  - Audit log of license operations
  - Export licenses to JSON/CSV
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from ..keygen.key_generator import generate_activation_key, generate_confirmation_code

logger = logging.getLogger(__name__)


# ── Data Types ───────────────────────────────────────────────


@dataclass
class ManagedLicense:
    """A license record managed by the admin system."""

    license_id: str
    activation_key: str
    confirmation_code: str
    tier: str
    issued_to: str
    issued_at: float
    expires_at: float
    status: str = "active"  # active | revoked | expired
    max_users: int = 1
    notes: str = ""


# ── License Database ─────────────────────────────────────────


class AdminLicenseDB:
    """Persistent storage for admin-managed licenses.

    Uses a local SQLite database (separate from user activation DB)
    to track all licenses issued by the admin.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.path.expanduser("~/.zenic/admin_licenses.sqlite")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                license_id TEXT PRIMARY KEY,
                activation_key TEXT NOT NULL,
                confirmation_code TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'starter',
                issued_to TEXT NOT NULL DEFAULT '',
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                max_users INTEGER NOT NULL DEFAULT 1,
                notes TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                license_id TEXT,
                details TEXT DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()

    def insert_license(self, lic: ManagedLicense) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO licenses "
            "(license_id, activation_key, confirmation_code, tier, issued_to, "
            "issued_at, expires_at, status, max_users, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                lic.license_id,
                lic.activation_key,
                lic.confirmation_code,
                lic.tier,
                lic.issued_to,
                lic.issued_at,
                lic.expires_at,
                lic.status,
                lic.max_users,
                lic.notes,
            ),
        )
        conn.commit()
        conn.close()

    def list_licenses(self, status: str | None = None) -> list[ManagedLicense]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        if status:
            rows = conn.execute(
                "SELECT * FROM licenses WHERE status = ? ORDER BY issued_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM licenses ORDER BY issued_at DESC"
            ).fetchall()
        conn.close()
        return [ManagedLicense(**dict(r)) for r in rows]

    def update_status(self, license_id: str, status: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        cur = conn.execute(
            "UPDATE licenses SET status = ? WHERE license_id = ?",
            (status, license_id),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def log_audit(self, action: str, license_id: str, details: str = "") -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO audit_log (timestamp, action, license_id, details) "
            "VALUES (?, ?, ?, ?)",
            (time.time(), action, license_id, details),
        )
        conn.commit()
        conn.close()

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ── License Manager CLI ──────────────────────────────────────


class LicenseManagerCLI:
    """Admin CLI for full license lifecycle management."""

    TIER_DURATIONS = {
        "trial": 14,
        "starter": 30,
        "business": 30,
        "enterprise": 365,
        "on_premise_enterprise": 0,  # perpetual
    }

    def __init__(self) -> None:
        self._db = AdminLicenseDB()

    def create_license(
        self,
        tier: str = "starter",
        issued_to: str = "",
        max_users: int = 1,
        expires_days: int | None = None,
        notes: str = "",
    ) -> ManagedLicense:
        """Create a new license with activation key + confirmation code pair."""
        import secrets

        now = time.time()
        if expires_days is None:
            expires_days = self.TIER_DURATIONS.get(tier, 30)
        expires_at = now + (expires_days * 86400) if expires_days > 0 else 0.0

        license_id = f"zl-{secrets.token_hex(8)}"
        activation_key = generate_activation_key()
        confirmation_code = generate_confirmation_code()

        lic = ManagedLicense(
            license_id=license_id,
            activation_key=activation_key,
            confirmation_code=confirmation_code,
            tier=tier,
            issued_to=issued_to,
            issued_at=now,
            expires_at=expires_at,
            status="active",
            max_users=max_users,
            notes=notes,
        )

        self._db.insert_license(lic)
        self._db.log_audit(
            "created", license_id,
            f"tier={tier}, issued_to={issued_to}, expires_days={expires_days}",
        )

        logger.info("License created: %s (tier=%s)", license_id, tier)
        return lic

    def create_bulk_licenses(
        self,
        count: int,
        tier: str = "starter",
        issued_to: str = "",
        notes: str = "",
    ) -> list[ManagedLicense]:
        """Create multiple licenses at once."""
        licenses = []
        for _ in range(count):
            lic = self.create_license(
                tier=tier, issued_to=issued_to, notes=notes
            )
            licenses.append(lic)
        return licenses

    def list_licenses(self, status: str | None = None) -> list[ManagedLicense]:
        """List all licenses, optionally filtered by status."""
        return self._db.list_licenses(status)

    def revoke_license(self, license_id: str, reason: str = "") -> bool:
        """Revoke a license."""
        success = self._db.update_status(license_id, "revoked")
        if success:
            self._db.log_audit(
                "revoked", license_id, reason or "Revoked by admin"
            )
            logger.info("License revoked: %s", license_id)
        return success

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._db.get_audit_log(limit)

    def export_licenses(self, format: str = "json") -> str:
        """Export all licenses in JSON or CSV format."""
        licenses = self.list_licenses()

        if format == "json":
            data = []
            for lic in licenses:
                data.append({
                    "license_id": lic.license_id,
                    "activation_key": lic.activation_key,
                    "confirmation_code": lic.confirmation_code,
                    "tier": lic.tier,
                    "issued_to": lic.issued_to,
                    "issued_at": lic.issued_at,
                    "expires_at": lic.expires_at,
                    "status": lic.status,
                    "max_users": lic.max_users,
                })
            return json.dumps({"licenses": data, "count": len(data)}, indent=2)

        elif format == "csv":
            lines = [
                "license_id,activation_key,confirmation_code,tier,issued_to,status"
            ]
            for lic in licenses:
                lines.append(
                    f"{lic.license_id},{lic.activation_key},{lic.confirmation_code},"
                    f"{lic.tier},{lic.issued_to},{lic.status}"
                )
            return "\n".join(lines)

        return "Unsupported format"


# ── CLI Entry Point ──────────────────────────────────────────


def main() -> None:
    """CLI entry point for license management."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="zenic-license-admin",
        description="Admin license management for Zenic-Agents",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new license")
    create_parser.add_argument("--tier", default="starter",
                               choices=["trial", "starter", "business", "enterprise", "on_premise_enterprise"])
    create_parser.add_argument("--issued-to", default="")
    create_parser.add_argument("--max-users", type=int, default=1)
    create_parser.add_argument("--expires-days", type=int, default=None)
    create_parser.add_argument("--notes", default="")

    # bulk
    bulk_parser = subparsers.add_parser("bulk", help="Create multiple licenses")
    bulk_parser.add_argument("--count", "-n", type=int, default=10)
    bulk_parser.add_argument("--tier", default="starter")
    bulk_parser.add_argument("--issued-to", default="")
    bulk_parser.add_argument("--notes", default="")

    # list
    list_parser = subparsers.add_parser("list", help="List licenses")
    list_parser.add_argument("--status", choices=["active", "revoked", "expired"])

    # revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a license")
    revoke_parser.add_argument("--license-id", "-l", required=True)
    revoke_parser.add_argument("--reason", default="")

    # audit
    subparsers.add_parser("audit", help="View audit log")

    # export
    export_parser = subparsers.add_parser("export", help="Export licenses")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json")

    args = parser.parse_args()
    cli = LicenseManagerCLI()

    if args.command == "create":
        lic = cli.create_license(
            tier=args.tier,
            issued_to=args.issued_to,
            max_users=args.max_users,
            expires_days=args.expires_days,
            notes=args.notes,
        )
        print(f"License created:")
        print(f"  ID:               {lic.license_id}")
        print(f"  Activation Key:   {lic.activation_key}")
        print(f"  Confirmation Code: {lic.confirmation_code}")
        print(f"  Tier:             {lic.tier}")
        print(f"  Issued To:        {lic.issued_to}")

    elif args.command == "bulk":
        licenses = cli.create_bulk_licenses(
            count=args.count,
            tier=args.tier,
            issued_to=args.issued_to,
            notes=args.notes,
        )
        print(f"Created {len(licenses)} licenses:")
        for lic in licenses:
            print(f"  {lic.license_id}: {lic.activation_key} [{lic.tier}]")

    elif args.command == "list":
        licenses = cli.list_licenses(status=args.status)
        if not licenses:
            print("No licenses found.")
            return
        print(f"{'ID':<24} {'Tier':<12} {'Status':<10} {'Issued To':<20}")
        print("-" * 70)
        for lic in licenses:
            print(f"{lic.license_id:<24} {lic.tier:<12} {lic.status:<10} {lic.issued_to:<20}")

    elif args.command == "revoke":
        success = cli.revoke_license(args.license_id, reason=args.reason)
        print(f"License {'REVOKED' if success else 'NOT FOUND'}")

    elif args.command == "audit":
        entries = cli.get_audit_log()
        print(f"{'Time':<24} {'Action':<12} {'License ID':<24} {'Details'}")
        print("-" * 80)
        for entry in entries:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
            print(f"{t:<24} {entry['action']:<12} {entry['license_id']:<24} {entry['details']}")

    elif args.command == "export":
        print(cli.export_licenses(format=args.format))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
