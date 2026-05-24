"""
Zenic-Agents — Onboarding CLI Entry Point (Phase 10)

Command-line interface for the User Onboarding TUI.
Provides argparse-based command routing with rich output.

Usage::

    zenic-onboard welcome                    Show welcome screen
    zenic-onboard register                   Register interactively
    zenic-onboard register -u USER -e EMAIL  Register with params
    zenic-onboard activate -k KEY            Activate a license key
    zenic-onboard activate                   Activate interactively
    zenic-onboard status                     Check license status
    zenic-onboard hardware                   Show hardware fingerprint
    zenic-onboard quickstart                 Full interactive onboarding
    zenic-onboard --version                  Show version
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Version ──────────────────────────────────────────────────

VERSION = "3.0.0"
ZENIC_FULL_NAME = "Zenic-Agents Onboarding TUI"


# ── Argument Parser ──────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured ArgumentParser with all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="zenic-onboard",
        description=f"{ZENIC_FULL_NAME} v{VERSION} — User onboarding and license activation",
        epilog=(
            "Examples:\n"
            "  zenic-onboard welcome\n"
            "  zenic-onboard register -u yurislay9 -e user@example.com\n"
            "  zenic-onboard activate -k ZENIC-XXXX-XXXX-XXXX-XXXX\n"
            "  zenic-onboard status\n"
            "  zenic-onboard hardware\n"
            "  zenic-onboard quickstart\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "--no-interactive", "-n",
        action="store_true",
        default=False,
        help="Disable interactive prompts (for scripting / CI)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results in JSON format",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available onboarding commands",
    )

    # ── Welcome ──────────────────────────────────────────────
    welcome_parser = subparsers.add_parser(
        "welcome",
        help="Show the welcome screen",
    )

    # ── Register ─────────────────────────────────────────────
    reg_parser = subparsers.add_parser(
        "register",
        help="Register as a new user",
    )
    reg_parser.add_argument(
        "--username", "-u",
        default="",
        help="Desired username (3-32 chars, letters/digits/underscore)",
    )
    reg_parser.add_argument(
        "--email", "-e",
        default="",
        help="Email address (permanent, no disposable domains)",
    )
    reg_parser.add_argument(
        "--device-name", "-d",
        default="",
        help="Human-readable device name",
    )
    reg_parser.add_argument(
        "--tier", "-t",
        choices=["starter", "business", "enterprise", "on_premise_enterprise", "trial"],
        default="starter",
        help="License tier (default: starter)",
    )
    reg_parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        default=False,
        help="Prompt for missing fields interactively",
    )

    # ── Activate ─────────────────────────────────────────────
    act_parser = subparsers.add_parser(
        "activate",
        help="Activate a license with an activation key",
    )
    act_parser.add_argument(
        "--key", "-k",
        default="",
        help="Activation key (ZENIC-XXXX-XXXX-XXXX-XXXX format)",
    )
    act_parser.add_argument(
        "--username", "-u",
        default="",
        help="Registered username (optional)",
    )
    act_parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        default=False,
        help="Prompt for key interactively",
    )

    # ── Status ───────────────────────────────────────────────
    status_parser = subparsers.add_parser(
        "status",
        help="Check current license status",
    )

    # ── Hardware ─────────────────────────────────────────────
    hw_parser = subparsers.add_parser(
        "hardware",
        help="Display hardware fingerprint and system info",
    )

    # ── Quickstart ───────────────────────────────────────────
    qs_parser = subparsers.add_parser(
        "quickstart",
        help="Run full interactive onboarding (welcome → register → activate → verify)",
    )

    # ── Validate ─────────────────────────────────────────────
    val_parser = subparsers.add_parser(
        "validate",
        help="Validate an activation key without activating it",
    )
    val_parser.add_argument(
        "--key", "-k",
        required=True,
        help="Activation key to validate",
    )

    return parser


# ── Command Handlers ─────────────────────────────────────────

def cmd_welcome(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'welcome' command."""
    app.show_welcome(version=VERSION)
    return 0


def cmd_register(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'register' command."""
    interactive = args.interactive or (not args.username and not args.email)

    result = app.register(
        username=args.username,
        email=args.email,
        device_name=args.device_name,
        tier=args.tier,
        interactive=interactive,
    )

    if args.json:
        _print_json(result)
    return 0 if result.success else 1


def cmd_activate(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'activate' command."""
    interactive = args.interactive or not args.key

    result = app.activate(
        key=args.key,
        username=args.username,
        interactive=interactive,
    )

    if args.json:
        _print_json(result)
    return 0 if result.success else 1


def cmd_status(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'status' command."""
    result = app.check_status()

    if args.json:
        _print_json(result)
    return 0 if result.success else 1


def cmd_hardware(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'hardware' command."""
    result = app.check_hardware()

    if args.json:
        _print_json(result)
    return 0 if result.success else 1


def cmd_quickstart(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'quickstart' command."""
    result = app.quick_start()

    if args.json:
        _print_json(result)
    return 0 if result.success else 1


def cmd_validate(app: "OnboardingTUI", args: argparse.Namespace) -> int:
    """Handle the 'validate' command."""
    from .validators.activation_key import validate_activation_key

    result = validate_activation_key(args.key)

    if args.json:
        import json
        print(json.dumps({
            "valid": result.is_valid,
            "error": result.error_message if not result.is_valid else None,
            "sanitized": result.sanitized_value if result.is_valid else None,
        }, indent=2))
    else:
        if result.is_valid:
            try:
                from rich.console import Console
                Console().print(f"[bold green]Valid activation key:[/] {result.sanitized_value}")
            except ImportError:
                print(f"Valid activation key: {result.sanitized_value}")
        else:
            try:
                from rich.console import Console
                Console().print(f"[bold red]Invalid activation key:[/] {result.error_message}")
            except ImportError:
                print(f"Invalid activation key: {result.error_message}")

    return 0 if result.is_valid else 1


# ── Command Router ───────────────────────────────────────────

COMMAND_MAP = {
    "welcome": cmd_welcome,
    "register": cmd_register,
    "activate": cmd_activate,
    "status": cmd_status,
    "hardware": cmd_hardware,
    "quickstart": cmd_quickstart,
    "validate": cmd_validate,
}


# ── JSON Output Helper ───────────────────────────────────────

def _print_json(result: "FlowResult") -> None:
    """Print a FlowResult as JSON."""
    import json
    print(json.dumps(result.to_dict(), indent=2))


# ── Main Entry Point ────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the onboarding CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # No command → show help
    if not args.command:
        parser.print_help()
        return 0

    # Lazy import to avoid circular imports
    from .app import OnboardingTUI

    # Create the TUI facade
    app = OnboardingTUI(no_interactive=args.no_interactive)

    # Route to command handler
    handler = COMMAND_MAP.get(args.command)
    if handler:
        try:
            return handler(app, args)
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return 130
        except Exception as exc:
            logger.error("Command '%s' failed: %s", args.command, exc)
            try:
                from rich.console import Console
                Console().print(f"[bold red]Error:[/] {exc}")
            except ImportError:
                print(f"Error: {exc}")
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
