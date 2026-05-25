"""
Zenic-Agents — Status Display Renderer (Phase 10)

Rich-based status panel renderer for license status information.
Supports tables, panels, and color-coded status indicators.

Design Patterns:
  - Strategy: Plain vs Rich rendering strategies
  - Flyweight: shared console instance
"""

from __future__ import annotations

from typing import Any

try:
    from rich.box import ROUNDED, SIMPLE
    from rich.columns import Columns  # noqa: F401
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text  # noqa: F401

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Status Color Mapping ─────────────────────────────────────

_STATUS_COLORS: dict[str, str] = {
    "active": "bold green",
    "trial": "bold cyan",
    "grace_period": "bold yellow",
    "expired": "bold red",
    "revoked": "bold white on red",
    "invalid": "red",
    "no_license": "dim",
    "pending_activation": "yellow",
}

_TIER_COLORS: dict[str, str] = {
    "starter": "white",
    "business": "bold cyan",
    "enterprise": "bold magenta",
    "on_premise_enterprise": "bold yellow",
    "trial": "cyan",
}


class StatusRenderer:
    """Renders license status as a Rich panel or plain text.

    Supports two modes:
      - Detailed: Full status report with tables
      - Compact: Single-line status indicator
    """

    def __init__(self, console: Console | None = None, compact: bool = False) -> None:
        self._console = console or (Console() if HAS_RICH else None)
        self._compact = compact

    def render(self, status_data: dict[str, Any]) -> str:
        """Render the status display.

        Args:
            status_data: Dictionary from StatusResult.to_dict() or similar.

        Returns:
            Formatted string for display.
        """
        if self._compact:
            return self._render_compact(status_data)

        if HAS_RICH and self._console:
            return self._render_rich(status_data)
        return self._render_plain(status_data)

    def _render_compact(self, data: dict[str, Any]) -> str:
        """Render a compact single-line status indicator."""
        status = data.get("status", "no_license")
        tier = data.get("tier", "none")
        valid = data.get("is_valid", False)

        icon = "+" if valid else "x"
        status_str = status.upper()
        tier_str = tier.upper()

        return f"[{icon}] {status_str} | Tier: {tier_str}"

    def _render_rich(self, data: dict[str, Any]) -> str:
        """Render with Rich tables and panels."""
        import io

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=64)

        status = data.get("status", "no_license")
        tier = data.get("tier", "none")
        valid = data.get("is_valid", False)

        # Status indicator
        status_color = _STATUS_COLORS.get(status, "white")
        tier_color = _TIER_COLORS.get(tier, "white")

        # Main status table
        table = Table(show_header=False, box=SIMPLE, padding=(0, 2))
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Status", f"[{status_color}]{status.upper()}[/]")
        table.add_row("Tier", f"[{tier_color}]{tier.upper()}[/]")
        table.add_row("Valid", "[green]Yes[/]" if valid else "[red]No[/]")
        table.add_row("License ID", data.get("license_id", "N/A"))

        # Expiration
        if data.get("is_perpetual"):
            table.add_row("Expires", "[bold green]PERPETUAL[/]")
        elif data.get("days_remaining") is not None:
            days = data["days_remaining"]
            color = "green" if days > 7 else ("yellow" if days > 0 else "red")
            table.add_row("Days Left", f"[{color}]{days}[/]")

        # Hardware
        if data.get("hardware_bound"):
            table.add_row("Hardware", "[green]Bound[/]")
        else:
            table.add_row("Hardware", "[dim]Unbound[/]")

        # Kill switch
        if data.get("kill_switch_active"):
            table.add_row("Kill Switch", "[bold red]ACTIVE[/]")

        console.print(Panel(table, title="[bold]License Status[/]", border_style="blue", box=ROUNDED))

        return buf.getvalue()

    def _render_plain(self, data: dict[str, Any]) -> str:
        """Render as plain text."""
        status = data.get("status", "no_license")
        tier = data.get("tier", "none")
        valid = data.get("is_valid", False)

        lines = [
            f"License Status: {status.upper()}",
            f"  Tier:       {tier.upper()}",
            f"  Valid:      {'Yes' if valid else 'No'}",
            f"  License ID: {data.get('license_id', 'N/A')}",
        ]

        if data.get("is_perpetual"):
            lines.append("  Expires:    PERPETUAL")
        elif data.get("days_remaining") is not None:
            lines.append(f"  Days Left:  {data['days_remaining']}")

        if data.get("hardware_bound"):
            lines.append("  Hardware:   Bound")
        else:
            lines.append("  Hardware:   Unbound")

        return "\n".join(lines)


# ── Convenience Function ────────────────────────────────────


def render_status_panel(data: dict[str, Any], compact: bool = False) -> str:
    """One-shot status panel rendering."""
    return StatusRenderer(compact=compact).render(data)
