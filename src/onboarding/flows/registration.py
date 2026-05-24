"""
Zenic-Agents — Registration Flow (Phase 10)

End-user registration flow that collects username, email, and
device info, then stores the registration locally in SQLite.

The registration data is used for license activation and
identifying the user in the Zenic ecosystem.

Design Patterns:
  - Template Method: extends BaseFlow lifecycle
  - Builder: RegistrationData built incrementally
  - Validator Chain: username/email validated via chain
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from ..validators.user_input import (
    EmailValidator,
    UsernameValidator,
)
from .base import BaseFlow, FlowContext

logger = logging.getLogger(__name__)


# ── Registration Data ────────────────────────────────────────


@dataclass
class RegistrationData:
    """Data collected during user registration.

    Attributes:
        username: Chosen username (validated).
        email: User email address (validated).
        device_name: Human-readable device name.
        device_id: Hardware fingerprint hash.
        registered_at: Unix timestamp of registration.
        registration_id: Unique registration identifier.
        tier_requested: Initial tier requested (default: starter).
    """

    username: str = ""
    email: str = ""
    device_name: str = ""
    device_id: str = ""
    registered_at: float = 0.0
    registration_id: str = ""
    tier_requested: str = "starter"

    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return bool(self.username and self.email and self.registration_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "username": self.username,
            "email": self.email,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "registered_at": self.registered_at,
            "registration_id": self.registration_id,
            "tier_requested": self.tier_requested,
        }

    def to_signable(self) -> str:
        """Create canonical string for signing."""
        return "|".join(
            [
                self.registration_id,
                self.username,
                self.email,
                self.device_id,
                str(self.registered_at),
            ]
        )


class RegistrationDataBuilder:
    """Builder for RegistrationData with validation at each step.

    Enforces that each field is set and validated before
    the final data object can be built.
    """

    def __init__(self) -> None:
        self._data = RegistrationData()
        self._errors: list[str] = []

    def set_username(self, username: str) -> RegistrationDataBuilder:
        """Set and validate the username."""
        validator = UsernameValidator()
        result = validator.validate(username)
        if result.is_valid:
            self._data.username = result.sanitized_value
        else:
            self._errors.append(result.error_message)
        return self

    def set_email(self, email: str) -> RegistrationDataBuilder:
        """Set and validate the email."""
        validator = EmailValidator()
        result = validator.validate(email)
        if result.is_valid:
            self._data.email = result.sanitized_value
        else:
            self._errors.append(result.error_message)
        return self

    def set_device_name(self, name: str) -> RegistrationDataBuilder:
        """Set the device name (no strict validation)."""
        self._data.device_name = name.strip()[:64] if name else "Unknown"
        return self

    def set_tier(self, tier: str) -> RegistrationDataBuilder:
        """Set the requested tier."""
        valid_tiers = ("starter", "business", "enterprise", "on_premise_enterprise", "trial")
        normalized = tier.lower().strip()
        self._data.tier_requested = normalized if normalized in valid_tiers else "starter"
        return self

    def build(self) -> RegistrationData:
        """Build the final RegistrationData object.

        Raises:
            ValueError: If any validation errors were collected.
        """
        if self._errors:
            raise ValueError(f"Registration validation failed: {'; '.join(self._errors)}")

        # Auto-generate fields
        if not self._data.registration_id:
            self._data.registration_id = f"reg-{secrets.token_hex(6)}"
        if not self._data.registered_at:
            self._data.registered_at = time.time()
        if not self._data.device_id:
            try:
                from src.core.license.license_parts.hw_binding import get_hardware_fingerprint

                self._data.device_id = get_hardware_fingerprint()
            except ImportError:
                self._data.device_id = hashlib.sha256(f"{self._data.username}:{time.time()}".encode()).hexdigest()[:32]

        return self._data


# ── Registration Persistence ─────────────────────────────────


class RegistrationStore:
    """SQLite-backed storage for registration data.

    Uses WAL mode for concurrent access and stores
    only one registration per device (latest wins).
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.path.expanduser("~/.zenic/registration.sqlite")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the registration database."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                registration_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                device_name TEXT DEFAULT '',
                device_id TEXT DEFAULT '',
                tier_requested TEXT DEFAULT 'starter',
                registered_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id TEXT NOT NULL,
                event TEXT NOT NULL,
                timestamp REAL NOT NULL,
                details TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()

    def save(self, data: RegistrationData) -> None:
        """Save registration data to the database."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO registrations "
            "(registration_id, username, email, device_name, device_id, "
            "tier_requested, registered_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.registration_id,
                data.username,
                data.email,
                data.device_name,
                data.device_id,
                data.tier_requested,
                data.registered_at,
                json.dumps({"version": "1.0"}),
            ),
        )
        conn.execute(
            "INSERT INTO registration_log (registration_id, event, timestamp, details) " "VALUES (?, ?, ?, ?)",
            (data.registration_id, "registered", time.time(), json.dumps(data.to_dict())),
        )
        conn.commit()
        conn.close()
        logger.info("Registration saved: %s (%s)", data.username, data.registration_id)

    def load(self) -> RegistrationData | None:
        """Load the most recent registration from the database."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM registrations ORDER BY registered_at DESC LIMIT 1").fetchone()
        conn.close()

        if row:
            return RegistrationData(
                registration_id=row["registration_id"],
                username=row["username"],
                email=row["email"],
                device_name=row["device_name"] or "",
                device_id=row["device_id"] or "",
                tier_requested=row["tier_requested"] or "starter",
                registered_at=row["registered_at"],
            )
        return None

    def exists(self) -> bool:
        """Check if a registration exists."""
        conn = sqlite3.connect(self._db_path)
        count = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
        conn.close()
        return count > 0


# ── Registration Flow ────────────────────────────────────────


class RegistrationFlow(BaseFlow):
    """End-user registration flow.

    Collects and validates user information, persists it locally,
    and prepares the user for license activation.

    Steps:
      1. Validate username and email
      2. Collect device info
      3. Persist registration data
      4. Generate confirmation for display
    """

    name = "registration"
    description = "Register as a new Zenic-Agents user"
    version = "1.0.0"

    def __init__(self, store: RegistrationStore | None = None) -> None:
        super().__init__()
        self._store = store or RegistrationStore()

    def on_validate(self, ctx: FlowContext) -> None:
        """Validate all required registration inputs."""
        username = ctx.get_input("username")
        email = ctx.get_input("email")

        if not username:
            raise ValueError("Username is required for registration")
        if not email:
            raise ValueError("Email is required for registration")

        # Validate username
        uname_result = UsernameValidator().validate(username)
        if not uname_result.is_valid:
            raise ValueError(f"Invalid username: {uname_result.error_message}")

        # Validate email
        email_result = EmailValidator().validate(email)
        if not email_result.is_valid:
            raise ValueError(f"Invalid email: {email_result.error_message}")

        # Check for existing registration
        if self._store.exists():
            existing = self._store.load()
            if existing and existing.username == username.strip():
                ctx.set_artifact("existing_registration", existing.to_dict())

    def on_execute(self, ctx: FlowContext) -> None:
        """Build and persist the registration data."""
        builder = RegistrationDataBuilder()
        builder.set_username(ctx.get_input("username"))
        builder.set_email(ctx.get_input("email"))
        builder.set_device_name(ctx.get_input("device_name"))
        builder.set_tier(ctx.get_input("tier"))

        reg_data = builder.build()
        self._store.save(reg_data)

        ctx.set_artifact("registration", reg_data.to_dict())
        ctx.set_artifact("registration_id", reg_data.registration_id)
        ctx.set_artifact("username", reg_data.username)

        logger.info(
            "RegistrationFlow: User '%s' registered as %s",
            reg_data.username,
            reg_data.registration_id,
        )

    def on_render(self, ctx: FlowContext) -> str:
        """Render registration result for display."""
        reg = ctx.get_artifact("registration", {})
        existing = ctx.get_artifact("existing_registration")

        if existing:
            return (
                f"[bold yellow]Registration already exists![/]\n\n"
                f"  Username:  {existing.get('username', 'N/A')}\n"
                f"  Email:     {existing.get('email', 'N/A')}\n"
                f"  Reg ID:    {existing.get('registration_id', 'N/A')}\n"
                f"  Device:    {existing.get('device_name', 'N/A')}\n\n"
                f"Use [bold]zenic-onboard activate[/] to activate your license."
            )

        return (
            f"[bold green]Registration Successful![/]\n\n"
            f"  Username:     {reg.get('username', 'N/A')}\n"
            f"  Email:        {reg.get('email', 'N/A')}\n"
            f"  Registration: {reg.get('registration_id', 'N/A')}\n"
            f"  Device:       {reg.get('device_name', 'N/A')}\n"
            f"  Tier:         {reg.get('tier_requested', 'starter')}\n\n"
            f"[dim]Next step: Activate your license with[/]\n"
            f"[bold cyan]  zenic-onboard activate --key ZENIC-XXXX-XXXX-XXXX-XXXX[/]"
        )

    def on_finalize(self, ctx: FlowContext) -> None:
        """Log registration completion."""
        reg_id = ctx.get_artifact("registration_id", "")
        logger.info("RegistrationFlow finalized: %s", reg_id)
