"""
Zenic-Agents — Onboarding TUI App Facade (Phase 10)

Central facade for the User Onboarding TUI. Orchestrates flows,
renderers, and prompts into a cohesive user experience.

Design Patterns:
  - Facade: simplified API for the entire onboarding system
  - Mediator: coordinates between flows, renderers, and prompts
  - Command: each action is an executable command
  - State Machine: tracks onboarding state across operations
"""

from __future__ import annotations

import logging
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from .flows.base import FlowResult, FlowRegistry, FlowState
from .flows.registration import RegistrationFlow, RegistrationStore
from .flows.activation import ActivationFlow
from .flows.status import StatusFlow
from .flows.hardware import HardwareFlow
from .renderers.welcome import WelcomeRenderer
from .renderers.progress import ProgressRenderer
from .prompts import prompt_registration, prompt_activation

logger = logging.getLogger(__name__)


# ── Onboarding State ─────────────────────────────────────────

class OnboardingState(str, Enum):
    """Overall onboarding state for the user.

    States:
      - FRESH:      No registration or license
      - REGISTERED: User has registered but no license
      - ACTIVATED:  User has an active license
      - EXPIRED:    License has expired
      - REVOKED:    License has been revoked
    """
    FRESH = "fresh"
    REGISTERED = "registered"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ── Onboarding TUI App ──────────────────────────────────────

class OnboardingTUI:
    """Facade for the Zenic-Agents User Onboarding TUI.

    Provides a high-level API for all onboarding operations:
      - Welcome screen display
      - User registration
      - License activation
      - Status checking
      - Hardware fingerprint display

    Coordinates between flows, renderers, and interactive prompts.

    Usage::

        app = OnboardingTUI()
        app.show_welcome()
        result = app.register(username="user", email="user@example.com")
        result = app.activate(key="ZENIC-XXXX-XXXX-XXXX-XXXX")
        status = app.check_status()
    """

    VERSION = "1.0.0"

    def __init__(self, no_interactive: bool = False) -> None:
        """Initialize the onboarding TUI.

        Args:
            no_interactive: If True, suppress interactive prompts
                           (useful for scripting / CI).
        """
        self._no_interactive = no_interactive
        self._registry = FlowRegistry()
        self._store = RegistrationStore()
        self._state = OnboardingState.FRESH
        self._last_result: Optional[FlowResult] = None
        self._event_log: List[Dict[str, Any]] = []

        # Register flows
        self._registry.register("registration", RegistrationFlow)
        self._registry.register("activation", ActivationFlow)
        self._registry.register("status", StatusFlow)
        self._registry.register("hardware", HardwareFlow)

        # Detect current state
        self._detect_state()

    # ── Properties ───────────────────────────────────────────

    @property
    def state(self) -> OnboardingState:
        return self._state

    @property
    def is_registered(self) -> bool:
        return self._state in (
            OnboardingState.REGISTERED,
            OnboardingState.ACTIVATED,
            OnboardingState.EXPIRED,
        )

    @property
    def is_activated(self) -> bool:
        return self._state == OnboardingState.ACTIVATED

    @property
    def available_flows(self) -> List[Dict[str, str]]:
        return self._registry.list_flows()

    @property
    def last_result(self) -> Optional[FlowResult]:
        return self._last_result

    # ── State Detection ──────────────────────────────────────

    def _detect_state(self) -> None:
        """Auto-detect the current onboarding state."""
        # Check for license first
        try:
            from src.core.license import get_license_manager
            manager = get_license_manager()
            if manager.is_licensed():
                self._state = OnboardingState.ACTIVATED
                return
            license_info = manager.get_current_license()
            if license_info:
                if license_info.status.value == "expired":
                    self._state = OnboardingState.EXPIRED
                elif license_info.status.value == "revoked":
                    self._state = OnboardingState.REVOKED
                return
        except ImportError:
            pass

        # Check activation DB
        import sqlite3
        db_path = os.path.expanduser("~/.zenic/activations.sqlite")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                count = conn.execute(
                    "SELECT COUNT(*) FROM activations"
                ).fetchone()[0]
                conn.close()
                if count > 0:
                    self._state = OnboardingState.ACTIVATED
                    return
            except Exception:
                pass

        # Check registration
        if self._store.exists():
            self._state = OnboardingState.REGISTERED
            return

        self._state = OnboardingState.FRESH

    # ── Event Logging ────────────────────────────────────────

    def _log_event(self, event: str, **details: Any) -> None:
        """Log an onboarding event."""
        entry = {
            "event": event,
            "timestamp": time.time(),
            "state": self._state.value,
            **details,
        }
        self._event_log.append(entry)
        logger.debug("OnboardingTUI: %s → %s", event, details)

    # ── Welcome Screen ───────────────────────────────────────

    def show_welcome(self, version: str = "3.0.0") -> str:
        """Display the welcome screen.

        Args:
            version: Zenic-Agents version string.

        Returns:
            Formatted welcome screen string.
        """
        self._log_event("welcome", version=version)
        renderer = WelcomeRenderer()
        output = renderer.render(version)

        try:
            from rich.console import Console
            console = Console()
            console.print(output)
        except ImportError:
            print(output)

        return output

    # ── Registration ─────────────────────────────────────────

    def register(self, username: str = "", email: str = "",
                 device_name: str = "", tier: str = "starter",
                 interactive: bool = False) -> FlowResult:
        """Register a new user.

        Can be called with explicit parameters or in interactive mode
        which will prompt for missing fields.

        Args:
            username: Desired username.
            email: User email address.
            device_name: Human-readable device name.
            tier: Requested license tier.
            interactive: If True, prompt for missing fields.

        Returns:
            FlowResult with registration outcome.
        """
        self._log_event("register_start", username=username, interactive=interactive)

        # Interactive mode: prompt for missing fields
        if interactive and not self._no_interactive:
            if not username or not email:
                prompt_result = prompt_registration()
                if not prompt_result:
                    self._log_event("register_cancelled")
                    return FlowResult(
                        success=False, state=FlowState.CANCELLED,
                        message="Registration cancelled by user",
                        flow_name="registration",
                    )
                username = username or prompt_result.get("username")
                email = email or prompt_result.get("email")
                device_name = device_name or prompt_result.get("device_name", "My Device")
                tier = tier if tier != "starter" else prompt_result.get("tier", "starter")

        # Validate required fields
        if not username or not email:
            return FlowResult(
                success=False, state=FlowState.FAILED,
                message="Username and email are required for registration",
                errors=["Missing required fields"],
                flow_name="registration",
            )

        # Execute the registration flow
        flow = RegistrationFlow(store=self._store)
        result = flow.run(user_input={
            "username": username,
            "email": email,
            "device_name": device_name,
            "tier": tier,
        })

        self._last_result = result

        if result.success:
            self._state = OnboardingState.REGISTERED
            self._log_event("register_success", registration_id=result.data.get("registration_id"))
        else:
            self._log_event("register_failed", errors=result.errors)

        # Display result
        self._display_result(result)

        return result

    # ── Activation ───────────────────────────────────────────

    def activate(self, key: str = "", username: str = "",
                 interactive: bool = False) -> FlowResult:
        """Activate a license with a ZENIC-xxxx key.

        Args:
            key: The ZENIC-XXXX-XXXX-XXXX-XXXX activation key.
            username: Registered username (optional).
            interactive: If True, prompt for missing fields.

        Returns:
            FlowResult with activation outcome including confirmation code.
        """
        self._log_event("activate_start", key_provided=bool(key), interactive=interactive)

        # Interactive mode
        if interactive and not self._no_interactive:
            if not key:
                prompt_result = prompt_activation()
                if not prompt_result:
                    self._log_event("activate_cancelled")
                    return FlowResult(
                        success=False, state=FlowState.CANCELLED,
                        message="Activation cancelled by user",
                        flow_name="activation",
                    )
                key = key or prompt_result.get("key")
                username = username or prompt_result.get("username")

        if not key:
            return FlowResult(
                success=False, state=FlowState.FAILED,
                message="Activation key is required",
                errors=["Missing activation key"],
                flow_name="activation",
            )

        # Execute the activation flow
        flow = ActivationFlow()
        result = flow.run(user_input={
            "key": key,
            "username": username,
        })

        self._last_result = result

        if result.success:
            self._state = OnboardingState.ACTIVATED
            self._log_event("activate_success",
                           license_id=result.data.get("license_id"),
                           tier=result.data.get("tier"))
        else:
            self._log_event("activate_failed", errors=result.errors)

        # Display result
        self._display_result(result)

        return result

    # ── Status Check ─────────────────────────────────────────

    def check_status(self) -> FlowResult:
        """Check the current license status.

        Returns:
            FlowResult with detailed status information.
        """
        self._log_event("status_check")

        flow = StatusFlow()
        result = flow.run()
        self._last_result = result

        # Update state based on status
        status = result.data.get("status", "no_license")
        if status == "active" or status == "trial":
            self._state = OnboardingState.ACTIVATED
        elif status == "expired":
            self._state = OnboardingState.EXPIRED
        elif status == "revoked":
            self._state = OnboardingState.REVOKED

        # Display result
        self._display_result(result)

        return result

    # ── Hardware Check ───────────────────────────────────────

    def check_hardware(self) -> FlowResult:
        """Display the hardware fingerprint and system info.

        Returns:
            FlowResult with hardware information.
        """
        self._log_event("hardware_check")

        flow = HardwareFlow()
        result = flow.run()
        self._last_result = result

        # Display result
        self._display_result(result)

        return result

    # ── Quick Start ──────────────────────────────────────────

    def quick_start(self) -> FlowResult:
        """Run the complete onboarding flow interactively.

        Guides the user through: Welcome → Register → Activate → Verify.

        Returns:
            FlowResult from the final step.
        """
        self._log_event("quick_start")

        # Progress tracker
        progress = ProgressRenderer(title="Zenic-Agents Onboarding")
        progress.add_step("welcome", "Show welcome screen")
        progress.add_step("register", "Register account")
        progress.add_step("activate", "Activate license")
        progress.add_step("verify", "Verify activation")

        # Step 1: Welcome
        progress.start_step("welcome")
        self.show_welcome()
        progress.complete_step("welcome")

        # Step 2: Register (if needed)
        progress.start_step("register")
        if self.is_registered:
            progress.skip_step("register")
        else:
            reg_result = self.register(interactive=True)
            if not reg_result.success:
                progress.fail_step("register", reg_result.message)
                return reg_result
            progress.complete_step("register")

        # Step 3: Activate (if needed)
        progress.start_step("activate")
        if self.is_activated:
            progress.skip_step("activate")
        else:
            act_result = self.activate(interactive=True)
            if not act_result.success:
                progress.fail_step("activate", act_result.message)
                return act_result
            progress.complete_step("activate")

        # Step 4: Verify
        progress.start_step("verify")
        verify_result = self.check_status()
        if verify_result.success:
            progress.complete_step("verify")
        else:
            progress.fail_step("verify", verify_result.message)

        # Show progress summary
        print(progress.render())

        return verify_result

    # ── Display Helper ───────────────────────────────────────

    def _display_result(self, result: FlowResult) -> None:
        """Display a flow result to the user."""
        if result.message:
            try:
                from rich.console import Console
                console = Console()
                console.print(result.message)
            except ImportError:
                # Strip Rich markup for plain display
                import re
                clean = re.sub(r'\[/?[^\]]*\]', '', result.message)
                print(clean)

        if result.errors:
            for error in result.errors:
                try:
                    from rich.console import Console
                    Console().print(f"[red]Error:[/] {error}")
                except ImportError:
                    print(f"Error: {error}")

    # ── Summary ──────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current onboarding state."""
        return {
            "state": self._state.value,
            "is_registered": self.is_registered,
            "is_activated": self.is_activated,
            "available_flows": self.available_flows,
            "last_result": self._last_result.to_dict() if self._last_result else None,
            "event_count": len(self._event_log),
            "version": self.VERSION,
        }
