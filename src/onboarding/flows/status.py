"""
Zenic-Agents — License Status Flow (Phase 10)

Flow for end users to check their current license status,
including tier, expiration, features, and hardware binding.

Design Patterns:
  - Template Method: extends BaseFlow lifecycle
  - Null Object: NoLicenseResult when no license is found
  - Facade: delegates to LicenseManager for verification
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .base import BaseFlow, FlowContext

logger = logging.getLogger(__name__)


# ── Status Result ────────────────────────────────────────────


@dataclass
class StatusResult:
    """Detailed license status information for display.

    Attributes:
        has_license: Whether any license is loaded.
        license_id: The license identifier.
        tier: License tier name.
        status: Current status string.
        is_valid: Whether the license passes verification.
        is_expired: Whether the license has expired.
        is_perpetual: Whether the license never expires.
        days_remaining: Days until expiration (None if perpetual).
        features: List of enabled features.
        hardware_bound: Whether the license is hardware-bound.
        kill_switch_active: Whether the kill switch is active.
        last_heartbeat: Timestamp of last heartbeat.
        signer_algorithm: Algorithm used for signing.
        checks_performed: Verification checks and their results.
    """

    has_license: bool = False
    license_id: str = ""
    tier: str = "none"
    status: str = "no_license"
    is_valid: bool = False
    is_expired: bool = False
    is_perpetual: bool = False
    days_remaining: int | None = None
    features: list[str] = field(default_factory=list)
    hardware_bound: bool = False
    kill_switch_active: bool = False
    last_heartbeat: float = 0.0
    signer_algorithm: str = ""
    checks_performed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "has_license": self.has_license,
            "license_id": self.license_id,
            "tier": self.tier,
            "status": self.status,
            "is_valid": self.is_valid,
            "is_expired": self.is_expired,
            "is_perpetual": self.is_perpetual,
            "days_remaining": self.days_remaining,
            "features": self.features,
            "hardware_bound": self.hardware_bound,
            "kill_switch_active": self.kill_switch_active,
            "last_heartbeat": self.last_heartbeat,
            "signer_algorithm": self.signer_algorithm,
            "checks_performed": self.checks_performed,
        }


# ── Status Flow ──────────────────────────────────────────────


class StatusFlow(BaseFlow):
    """License status check flow for end users.

    Loads the current license, runs full verification, and
    displays a comprehensive status report including tier,
    expiration, features, and hardware binding info.

    Steps:
      1. Load current license from LicenseManager
      2. Run verification checks
      3. Collect detailed status
      4. Render formatted report
    """

    name = "status"
    description = "Check your current license status and details"
    version = "1.0.0"

    def on_validate(self, ctx: FlowContext) -> None:
        """No user input required for status check."""
        pass

    def on_execute(self, ctx: FlowContext) -> None:
        """Load license and run verification."""
        try:
            from src.core.license import (
                LicenseStatus,
                get_license_manager,
            )

            manager = get_license_manager()

            # Run full verification
            verification = manager.verify()
            license_info = verification.license_info
            status_dict = manager.get_status()

            # Build status result
            status = StatusResult(
                has_license=license_info is not None,
                license_id=status_dict.get("license_id", ""),
                tier=status_dict.get("tier", "none"),
                status=status_dict.get("status", "no_license"),
                is_valid=verification.valid,
                is_expired=license_info.is_expired() if license_info else False,
                is_perpetual=license_info.is_perpetual() if license_info else False,
                days_remaining=license_info.days_remaining() if license_info else None,
                features=status_dict.get("features", []),
                hardware_bound=status_dict.get("hardware_bound", False),
                kill_switch_active=status_dict.get("kill_switch_active", False),
                last_heartbeat=status_dict.get("last_heartbeat", 0.0),
                signer_algorithm=(status_dict.get("signer_using_fallback", True) and "hmac-sha256") or "ecdsa-p256",
                checks_performed=verification.checks_performed,
            )

            ctx.set_artifact("status", status.to_dict())
            ctx.set_artifact("verification_reason", verification.reason)

            if license_info:
                ctx.set_artifact("issued_to", license_info.issued_to)
                ctx.set_artifact("binding_strength", license_info.binding_strength.value)

        except ImportError:
            # LicenseManager not available — check activation DB directly
            ctx.set_artifact("status", StatusResult().to_dict())
            ctx.set_artifact("fallback", True)
            self._check_activation_db(ctx)

    def _check_activation_db(self, ctx: FlowContext) -> None:
        """Fallback: check activation database directly."""
        import sqlite3

        db_path = __import__("os").path.expanduser("~/.zenic/activations.sqlite")

        if not __import__("os").path.exists(db_path):
            return

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM activations ORDER BY activated_at DESC LIMIT 1").fetchone()
            conn.close()

            if row:
                status = StatusResult(
                    has_license=True,
                    license_id=row["license_id"],
                    tier=row["tier"],
                    status="active",
                    is_valid=True,
                    hardware_bound=bool(row["device_id"]),
                )
                expires_at = row["expires_at"]
                if expires_at > 0:
                    status.is_expired = time.time() > expires_at
                    status.days_remaining = max(0, int((expires_at - time.time()) / 86400))
                    status.is_valid = not status.is_expired
                else:
                    status.is_perpetual = True

                ctx.set_artifact("status", status.to_dict())
        except Exception as exc:
            logger.warning("StatusFlow: Fallback DB check failed: %s", exc)

    def on_render(self, ctx: FlowContext) -> str:
        """Render a formatted license status report."""
        status = ctx.get_artifact("status", StatusResult().to_dict())
        reason = ctx.get_artifact("verification_reason", "")
        fallback = ctx.get_artifact("fallback", False)

        if not status.get("has_license", False):
            return (
                "[bold red]No License Found[/]\n\n"
                "You don't have an active license yet.\n\n"
                "[bold]Get started:[/]\n"
                "  1. Register:  [cyan]zenic-onboard register --username NAME --email EMAIL[/]\n"
                "  2. Activate:  [cyan]zenic-onboard activate --key ZENIC-XXXX-XXXX-XXXX-XXXX[/]\n"
                f"\n[dim]{'(Fallback mode — LicenseManager unavailable)' if fallback else ''}[/]"
            )

        # Determine status color
        status_val = status.get("status", "unknown")
        color_map = {
            "active": "green",
            "trial": "cyan",
            "grace_period": "yellow",
            "expired": "red",
            "revoked": "bold red",
            "invalid": "red",
            "no_license": "red",
        }
        color = color_map.get(status_val, "white")

        lines = [
            "[bold]License Status Report[/]",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"  Status:        [{color}]{status_val.upper()}[/]",
            f"  License ID:    {status.get('license_id', 'N/A')}",
            f"  Tier:          [bold cyan]{status.get('tier', 'N/A').upper()}[/]",
            f"  Valid:         {'[green]Yes[/]' if status.get('is_valid') else '[red]No[/]'}",
        ]

        # Expiration
        if status.get("is_perpetual"):
            lines.append("  Expires:       [bold green]PERPETUAL[/] (never expires)")
        elif status.get("days_remaining") is not None:
            days = status["days_remaining"]
            days_color = "green" if days > 7 else ("yellow" if days > 0 else "red")
            lines.append(f"  Expires in:    [{days_color}]{days} days[/]")
            if status.get("is_expired"):
                lines.append("  [bold red]⚠ LICENSE HAS EXPIRED[/]")

        # Hardware binding
        if status.get("hardware_bound"):
            lines.append("  Hardware:      [green]Bound[/] (device-locked)")
        else:
            lines.append("  Hardware:      [dim]Unbound[/]")

        # Kill switch
        if status.get("kill_switch_active"):
            lines.append("  [bold red]⚠ KILL SWITCH ACTIVE[/]")

        # Features
        features = status.get("features", [])
        if features:
            if "all" in features:
                lines.append("  Features:      [green]All features unlocked[/]")
            else:
                lines.append(f"  Features:      {len(features)} enabled")
                # Show key features
                key_features = [
                    f
                    for f in features
                    if f
                    in (
                        "basic_pipeline",
                        "full_pipeline",
                        "app_generation",
                        "automation_generation",
                        "thinking_engine",
                        "reasoning_engine",
                        "logic_chains",
                    )
                ]
                if key_features:
                    for feat in key_features[:5]:
                        lines.append(f"    - {feat}")
                    if len(features) > 5:
                        lines.append(f"    ... and {len(features) - 5} more")

        # Checks performed
        checks = status.get("checks_performed", [])
        if checks:
            lines.append("")
            lines.append("[dim]Verification checks:[/]")
            for check in checks:
                check_color = "green" if ":ok" in check else ("red" if ":FAIL" in check else "yellow")
                lines.append(f"  [{check_color}]  {check}[/]")

        if reason:
            lines.append(f"\n  Reason: {reason}")

        if fallback:
            lines.append("\n[dim](Fallback mode — LicenseManager unavailable)[/]")

        return "\n".join(lines)
