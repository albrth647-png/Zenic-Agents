"""
Zenic-Agents — Welcome Screen Renderer (Phase 10)

Rich-based welcome screen for the onboarding TUI.
Displays ASCII art, version info, and quick-start guide.

Design Patterns:
  - Template Method: render sections in fixed order
  - Flyweight: shared console instance
"""

from __future__ import annotations

import os
import platform

try:
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# ── ASCII Art ────────────────────────────────────────────────

_ZENIC_BANNER = r"""
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ███████╗███████╗███╗   ██╗██╗███████╗███████╗██╗      ║
  ║   ╚══███╔╝██╔════╝████╗  ██║██║██╔════╝██╔════╝██║      ║
  ║     ███╔╝ █████╗  ██╔██╗ ██║██║███████╗█████╗  ██║      ║
  ║    ███╔╝  ██╔══╝  ██║╚██╗██║██║╚════██║██╔══╝  ██║      ║
  ║   ███████╗███████╗██║ ╚████║██║███████║███████╗███████╗  ║
  ║   ╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝╚══════╝╚══════╝  ║
  ║                                                           ║
  ║          A G E N T S   v3.0.0                             ║
  ║          Motor de IA Quirurgico Local                     ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
"""

class WelcomeRenderer:
    """Renders the onboarding welcome screen with Rich.

    Sections:
      1. ASCII art banner
      2. Version and system info
      3. Quick-start commands
      4. Environment detection (Android/Termux)
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or (Console() if HAS_RICH else None)

    def render(self, version: str = "3.0.0") -> str:
        """Render the complete welcome screen.

        Args:
            version: The Zenic-Agents version string.

        Returns:
            Formatted string for display (Rich markup or plain text).
        """
        if HAS_RICH and self._console:
            return self._render_rich(version)
        return self._render_plain(version)

    def _render_rich(self, version: str) -> str:
        """Render with Rich formatting."""
        import io

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=70)

        # Banner
        banner = Text(_ZENIC_BANNER, style="bold cyan")
        console.print(Align.center(banner))

        # Version info
        is_android = "ANDROID_ARGUMENT" in os.environ
        is_termux = "TERMUX_VERSION" in os.environ
        env_label = "Android/Termux" if (is_android or is_termux) else platform.system()

        info_text = Text.from_markup(
            f"  [bold]Version:[/]     {version}\n"
            f"  [bold]Platform:[/]   {env_label} ({platform.machine()})\n"
            f"  [bold]Python:[/]     {platform.python_version()}\n"
            f"  [bold]License:[/]    [dim]Not activated[/]"
        )
        console.print(Panel(info_text, title="[bold]Zenic-Agents[/]", border_style="bright_blue", box=ROUNDED))

        # Quick-start
        commands = Text.from_markup(
            "  [bold cyan]zenic-onboard register[/]   Create your account\n"
            "  [bold cyan]zenic-onboard activate[/]   Activate a license key\n"
            "  [bold cyan]zenic-onboard status[/]     Check license status\n"
            "  [bold cyan]zenic-onboard hardware[/]   View device fingerprint\n"
            "  [bold cyan]zenic-onboard --help[/]      Show all commands"
        )
        console.print(Panel(commands, title="[bold]Quick Start[/]", border_style="green", box=ROUNDED))

        # Android notice
        if is_android or is_termux:
            notice = Text.from_markup(
                "  [bold green]Android/Termux detected![/]\n"
                "  Zenic-Agents is optimized for mobile deployment.\n"
                "  All features work in Termux with proot-distro."
            )
            console.print(Panel(notice, border_style="yellow", box=ROUNDED))

        return buf.getvalue()

    def _render_plain(self, version: str) -> str:
        """Render as plain text (no Rich)."""
        is_android = "ANDROID_ARGUMENT" in os.environ
        is_termux = "TERMUX_VERSION" in os.environ
        env_label = "Android/Termux" if (is_android or is_termux) else platform.system()

        return (
            f"{_ZENIC_BANNER}\n"
            f"  Version:    {version}\n"
            f"  Platform:   {env_label} ({platform.machine()})\n"
            f"  Python:     {platform.python_version()}\n\n"
            f"  Quick Start:\n"
            f"    zenic-onboard register    Create your account\n"
            f"    zenic-onboard activate    Activate a license key\n"
            f"    zenic-onboard status      Check license status\n"
            f"    zenic-onboard hardware    View device fingerprint\n"
            f"    zenic-onboard --help       Show all commands\n"
        )

# ── Convenience Function ────────────────────────────────────

def render_welcome(version: str = "3.0.0") -> str:
    """One-shot welcome screen rendering."""
    return WelcomeRenderer().render(version)
