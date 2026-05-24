"""
Zenic-Agents — License Activation Flow (Phase 10)

Core activation flow for end users to activate their Zenic license
using a ZENIC-xxxx activation key. The flow validates the key,
communicates with the Firebase broker (if available), binds to
hardware, and returns the confirmation code (CONF-xxxxxxxx).

Design Patterns:
  - Template Method: extends BaseFlow lifecycle
  - Strategy: activation strategy varies by key source (manual / file / env)
  - Null Object: OfflineActivationStrategy when no Firebase is configured
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from .base import BaseFlow, FlowContext, FlowResult
from ..validators.activation_key import (
    ActivationKeyValidator,
    ConfirmationCodeValidator,
    validate_activation_key,
    ActivationKey,
    ConfirmationCode,
    generate_activation_key,
    generate_confirmation_code,
)

logger = logging.getLogger(__name__)


# ── Activation Result ────────────────────────────────────────

@dataclass
class ActivationResult:
    """Result of a license activation attempt.

    Attributes:
        activated: Whether the activation was successful.
        license_id: The assigned license ID (zl-xxxx).
        activation_key: The activation key used (masked).
        confirmation_code: CONF-xxxxxxxx code for user verification.
        tier: The activated license tier.
        expires_at: License expiration timestamp (0 = perpetual).
        device_id: Hardware fingerprint bound to this license.
        activated_at: Timestamp of activation.
        activation_method: How the activation was performed (online/offline).
    """
    activated: bool = False
    license_id: str = ""
    activation_key: str = ""
    confirmation_code: str = ""
    tier: str = ""
    expires_at: float = 0.0
    device_id: str = ""
    activated_at: float = 0.0
    activation_method: str = "offline"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "activated": self.activated,
            "license_id": self.license_id,
            "activation_key": self.activation_key,
            "confirmation_code": self.confirmation_code,
            "tier": self.tier,
            "expires_at": self.expires_at,
            "device_id": self.device_id,
            "activated_at": self.activated_at,
            "activation_method": self.activation_method,
        }


# ── Activation Strategy Protocol ─────────────────────────────

class ActivationStrategy(Protocol):
    """Protocol for activation strategies.

    Supports different activation backends:
      - OfflineActivation: Local-only activation with self-signed keys
      - OnlineActivation: Firebase broker-mediated activation
    """

    def activate(self, key: str, device_id: str, username: str) -> ActivationResult:
        """Attempt activation with the given key and device info."""
        ...


class OfflineActivationStrategy:
    """Local offline activation strategy.

    Validates the key format, creates a local license, and generates
    a confirmation code. Used when no Firebase broker is available
    or when the user has a pre-validated key.
    """

    def __init__(self) -> None:
        self._db_path = os.path.expanduser("~/.zenic/activations.sqlite")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the activation database."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activations (
                license_id TEXT PRIMARY KEY,
                activation_key TEXT NOT NULL,
                confirmation_code TEXT NOT NULL,
                tier TEXT NOT NULL,
                device_id TEXT DEFAULT '',
                username TEXT DEFAULT '',
                expires_at REAL DEFAULT 0,
                activated_at REAL NOT NULL,
                activation_method TEXT DEFAULT 'offline',
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()

    def activate(self, key: str, device_id: str, username: str) -> ActivationResult:
        """Perform offline activation.

        Validates the key, creates a local license entry, and
        generates a confirmation code for user verification.
        """
        # Validate the key
        result = validate_activation_key(key)
        if not result.is_valid:
            return ActivationResult(
                activated=False,
                activation_key=key[:20] + "...",
            )

        # Parse the key to extract tier info from the first data group
        # Convention: first char of first group encodes tier
        tier_map = {
            "S": "starter",
            "B": "business",
            "E": "enterprise",
            "O": "on_premise_enterprise",
            "T": "trial",
        }
        try:
            key_obj = ActivationKey.parse(key)
            first_char = key_obj.groups[0][0]
            tier = tier_map.get(first_char, "starter")
        except ValueError:
            tier = "starter"

        # Generate license ID and confirmation code
        license_id = f"zl-{secrets.token_hex(8)}"
        conf_code = generate_confirmation_code()

        # Compute expiration based on tier
        now = time.time()
        tier_duration_days = {
            "trial": 14,
            "starter": 30,
            "business": 30,
            "enterprise": 365,
            "on_premise_enterprise": 0,  # perpetual
        }
        days = tier_duration_days.get(tier, 30)
        expires_at = now + (days * 86400) if days > 0 else 0.0

        # Persist
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO activations "
            "(license_id, activation_key, confirmation_code, tier, device_id, "
            "username, expires_at, activated_at, activation_method, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (license_id, key.upper().strip(), conf_code, tier, device_id,
             username, expires_at, now, "offline",
             json.dumps({"key_masked": key_obj.masked() if 'key_obj' in dir() else key[:20]})),
        )
        conn.commit()
        conn.close()

        logger.info("OfflineActivation: %s activated (tier=%s)", license_id, tier)

        return ActivationResult(
            activated=True,
            license_id=license_id,
            activation_key=key.upper().strip(),
            confirmation_code=conf_code,
            tier=tier,
            expires_at=expires_at,
            device_id=device_id,
            activated_at=now,
            activation_method="offline",
        )


class OnlineActivationStrategy:
    """Firebase-mediated online activation strategy.

    Sends the activation key to the Firebase Realtime DB broker,
    waits for admin confirmation, and retrieves the license.

    Falls back to OfflineActivation if Firebase is unavailable.
    """

    FIREBASE_TIMEOUT: float = 30.0  # seconds to wait for admin response

    def __init__(self, firebase_url: Optional[str] = None,
                 firebase_key: Optional[str] = None) -> None:
        self._firebase_url = firebase_url or os.environ.get("ZENIC_FIREBASE_URL", "")
        self._firebase_key = firebase_key or os.environ.get("ZENIC_FIREBASE_KEY", "")
        self._offline = OfflineActivationStrategy()

    def activate(self, key: str, device_id: str, username: str) -> ActivationResult:
        """Attempt online activation via Firebase, fallback to offline.

        Online flow:
          1. POST activation request to Firebase
          2. Wait for admin to confirm (polling with timeout)
          3. Retrieve signed license from Firebase

        If Firebase is unavailable, falls back to offline activation.
        """
        if not self._firebase_url:
            logger.info("OnlineActivation: No Firebase URL configured, using offline")
            return self._offline.activate(key, device_id, username)

        try:
            # Post activation request
            import urllib.request
            request_data = json.dumps({
                "activation_key": key,
                "device_id": device_id,
                "username": username,
                "timestamp": time.time(),
                "nonce": secrets.token_hex(8),
            }).encode()

            url = f"{self._firebase_url}/activation_requests.json"
            if self._firebase_key:
                url += f"?auth={self._firebase_key}"

            req = urllib.request.Request(
                url, data=request_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                push_result = json.loads(resp.read().decode())
                request_id = push_result.get("name", "")

            if not request_id:
                logger.warning("OnlineActivation: Failed to post request, falling back")
                return self._offline.activate(key, device_id, username)

            logger.info("OnlineActivation: Request posted as %s, waiting for admin...", request_id)

            # For now, fall back to offline while admin processes
            # In production, this would poll for admin response
            result = self._offline.activate(key, device_id, username)
            result.activation_method = "online_fallback"
            return result

        except Exception as exc:
            logger.warning("OnlineActivation: Firebase error: %s, falling back", exc)
            return self._offline.activate(key, device_id, username)


# ── Activation Flow ──────────────────────────────────────────

class ActivationFlow(BaseFlow):
    """End-user license activation flow.

    Validates the ZENIC-xxxx key, performs activation (online or
    offline), binds to hardware, and returns the confirmation code.

    Steps:
      1. Validate the activation key format + checksum
      2. Resolve the activation strategy (online/offline)
      3. Execute activation
      4. Store result and display confirmation code
    """

    name = "activation"
    description = "Activate your Zenic-Agents license with an activation key"
    version = "1.0.0"

    def __init__(self, strategy: Optional[ActivationStrategy] = None) -> None:
        super().__init__()
        if strategy is not None:
            self._strategy = strategy
        elif os.environ.get("ZENIC_FIREBASE_URL"):
            self._strategy = OnlineActivationStrategy()
        else:
            self._strategy = OfflineActivationStrategy()

    def on_validate(self, ctx: FlowContext) -> None:
        """Validate the activation key."""
        key = ctx.get_input("key")
        if not key:
            raise ValueError("Activation key is required. Usage: --key ZENIC-XXXX-XXXX-XXXX-XXXX")

        result = validate_activation_key(key)
        if not result.is_valid:
            raise ValueError(f"Invalid activation key: {result.error_message}")

        ctx.set_artifact("validated_key", result.sanitized_value)

    def on_execute(self, ctx: FlowContext) -> None:
        """Execute the activation with the chosen strategy."""
        key = ctx.get_artifact("validated_key", "")
        username = ctx.get_input("username", "unknown")

        # Get hardware fingerprint
        device_id = ""
        try:
            from src.core.license.license_parts.hw_binding import get_hardware_fingerprint
            device_id = get_hardware_fingerprint()
        except ImportError:
            device_id = hashlib.sha256(f"device:{time.time()}".encode()).hexdigest()[:32]

        ctx.set_artifact("device_id", device_id)

        # Execute activation strategy
        activation_result = self._strategy.activate(key, device_id, username)

        if not activation_result.activated:
            raise ValueError("Activation failed — the key could not be activated")

        # Store result artifacts
        ctx.set_artifact("activation_result", activation_result.to_dict())
        ctx.set_artifact("license_id", activation_result.license_id)
        ctx.set_artifact("confirmation_code", activation_result.confirmation_code)
        ctx.set_artifact("tier", activation_result.tier)

        # Also try to register with LicenseManager
        try:
            from src.core.license import (
                LicenseManager, LicenseTier, LicenseStatus,
                HardwareBindingStrength, get_license_manager,
            )
            manager = get_license_manager()
            tier_map = {
                "starter": LicenseTier.STARTER,
                "business": LicenseTier.BUSINESS,
                "enterprise": LicenseTier.ENTERPRISE,
                "on_premise_enterprise": LicenseTier.ON_PREMISE_ENTERPRISE,
                "trial": LicenseTier.TRIAL,
            }
            license_tier = tier_map.get(activation_result.tier, LicenseTier.STARTER)

            days_map = {"trial": 14, "starter": 30, "business": 30, "enterprise": 365, "on_premise_enterprise": 0}
            expires_days = days_map.get(activation_result.tier, 30)

            license_info = manager.create_license(
                tier=license_tier,
                issued_to=username,
                expires_days=expires_days,
                hardware_binding=HardwareBindingStrength.SOFT,
            )
            ctx.set_artifact("license_info", license_info.to_dict())
        except Exception as exc:
            logger.warning("ActivationFlow: LicenseManager integration failed: %s", exc)

        logger.info(
            "ActivationFlow: Key activated → %s (tier=%s, method=%s)",
            activation_result.license_id, activation_result.tier,
            activation_result.activation_method,
        )

    def on_render(self, ctx: FlowContext) -> str:
        """Render activation result with confirmation code."""
        result = ctx.get_artifact("activation_result", {})
        conf_code = ctx.get_artifact("confirmation_code", "N/A")
        license_id = ctx.get_artifact("license_id", "N/A")
        tier = ctx.get_artifact("tier", "N/A")

        lines = [
            "[bold green]License Activated Successfully![/]",
            "",
            f"  License ID:       [bold]{license_id}[/]",
            f"  Tier:             [bold cyan]{tier.upper()}[/]",
            f"  Activation:       {result.get('activation_method', 'offline')}",
            "",
            "[bold yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
            f"[bold yellow]  Confirmation Code: [bold white on red]{conf_code}[/]",
            "[bold yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
            "",
            "[dim]Save this confirmation code in a safe place.[/]",
            "[dim]You may need it to verify your license or for support.[/]",
            "",
            f"  Device:  {ctx.get_artifact('device_id', 'N/A')[:16]}...",
            "",
            "[bold]Next steps:[/]",
            "  1. Run [cyan]zenic-onboard status[/] to verify your license",
            "  2. Start using Zenic-Agents!",
        ]

        # Add expiration info
        expires_at = result.get("expires_at", 0)
        if expires_at > 0:
            days_left = int((expires_at - time.time()) / 86400)
            lines.append(f"  License expires in [bold]{days_left}[/] days")
        else:
            lines.append("  License is [bold green]PERPETUAL[/] (never expires)")

        return "\n".join(lines)

    def on_finalize(self, ctx: FlowContext) -> None:
        """Cleanup after activation."""
        conf_code = ctx.get_artifact("confirmation_code", "")
        logger.info("ActivationFlow finalized. Confirmation: %s", conf_code)
