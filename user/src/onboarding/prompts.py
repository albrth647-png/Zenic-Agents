"""
Zenic-Agents — Interactive Prompts for Onboarding (Phase 10)

Interactive input collection for the onboarding TUI.
Supports Rich-styled prompts with validation feedback,
password masking, and choice selection.

Design Patterns:
  - Strategy: different prompt strategies (simple, validated, choice)
  - Template Method: BasePrompt defines prompt-render-validate loop
  - Builder: PromptBuilder for composing multi-field prompts
"""

from __future__ import annotations

import getpass
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .validators.user_input import InvalidResult, ValidationResult

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt as RichPrompt
    from rich.text import Text  # noqa: F401

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Prompt Result ────────────────────────────────────────────


@dataclass
class PromptResult:
    """Result of an interactive prompt session.

    Attributes:
        values: Collected key-value pairs from prompts.
        cancelled: Whether the user cancelled the prompt.
        errors: Validation errors encountered.
    """

    values: dict[str, str] = field(default_factory=dict)
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def __bool__(self) -> bool:
        return not self.cancelled and not self.errors


# ── Abstract Prompt ──────────────────────────────────────────


class BasePrompt(ABC):
    """Abstract base for interactive prompts.

    Subclasses implement the rendering and collection logic
    for different prompt types.
    """

    def __init__(
        self,
        field_name: str,
        label: str,
        validator: Callable[[str], ValidationResult] | None = None,
        default: str = "",
        required: bool = True,
        mask: bool = False,
    ) -> None:
        self.field_name = field_name
        self.label = label
        self.validator = validator
        self.default = default
        self.required = required
        self.mask = mask

    @abstractmethod
    def collect(self) -> tuple[str, bool]:
        """Collect input from the user.

        Returns:
            Tuple of (value, is_valid).
        """
        ...

    def validate(self, value: str) -> ValidationResult:
        """Validate the collected value."""
        if not value and self.required:
            return InvalidResult(f"{self.label} is required")
        if not value and not self.required:
            return ValidationResult(is_valid=True, sanitized_value=value)
        if self.validator:
            return self.validator(value)
        return ValidationResult(is_valid=True, sanitized_value=value.strip())

    def display_label(self) -> str:
        """Get the display label with required indicator."""
        suffix = " *" if self.required else ""
        default_hint = f" [{self.default}]" if self.default else ""
        return f"{self.label}{suffix}{default_hint}"


# ── Text Prompt ──────────────────────────────────────────────


class TextPrompt(BasePrompt):
    """Simple text input prompt with optional validation."""

    def collect(self) -> tuple[str, bool]:
        """Collect text input from the user."""
        if HAS_RICH:
            return self._collect_rich()
        return self._collect_plain()

    def _collect_rich(self) -> tuple[str, bool]:
        """Collect using Rich prompt."""
        try:
            console = Console()
            if self.mask:
                value = getpass.getpass(f"  {self.display_label()}: ")
            else:
                value = RichPrompt.ask(f"  {self.display_label()}", default=self.default, console=console)

            result = self.validate(value)
            if not result.is_valid:
                console.print(f"  [red]Error:[] {result.error_message}")
                return (value, False)
            return (result.sanitized_value, True)
        except (KeyboardInterrupt, EOFError):
            return ("", False)

    def _collect_plain(self) -> tuple[str, bool]:
        """Collect using plain input()."""
        try:
            if self.mask:
                value = getpass.getpass(f"  {self.display_label()}: ")
            else:
                prompt_text = f"  {self.display_label()}: "
                value = input(prompt_text).strip()

            if not value and self.default:
                value = self.default

            result = self.validate(value)
            if not result.is_valid:
                print(f"  Error: {result.error_message}")
                return (value, False)
            return (result.sanitized_value, True)
        except (KeyboardInterrupt, EOFError):
            return ("", False)


# ── Choice Prompt ────────────────────────────────────────────


class ChoicePrompt(BasePrompt):
    """Multiple-choice selection prompt."""

    def __init__(
        self,
        field_name: str,
        label: str,
        choices: list[tuple[str, str]],
        validator: Callable[[str], ValidationResult] | None = None,
        default: str = "",
        required: bool = True,
    ) -> None:
        """
        Args:
            choices: List of (value, description) tuples.
        """
        super().__init__(field_name, label, validator, default, required, mask=False)
        self.choices = choices

    def collect(self) -> tuple[str, bool]:
        """Collect choice input from the user."""
        if HAS_RICH:
            return self._collect_rich()
        return self._collect_plain()

    def _collect_rich(self) -> tuple[str, bool]:
        """Collect using Rich-styled choice display."""
        try:
            console = Console()
            console.print(f"\n  [bold]{self.label}[/]")
            for i, (value, desc) in enumerate(self.choices, 1):
                console.print(f"    [cyan]{i}[/]. {desc}")

            raw = RichPrompt.ask(
                f"  Select (1-{len(self.choices)})",
                default="1",
                console=console,
            )

            try:
                idx = int(raw) - 1
                if 0 <= idx < len(self.choices):
                    value = self.choices[idx][0]
                    result = self.validate(value)
                    if result.is_valid:
                        return (result.sanitized_value, True)
                    console.print(f"  [red]Error:[/] {result.error_message}")
                    return (value, False)
                console.print(f"  [red]Invalid choice: {raw}[/]")
                return (raw, False)
            except ValueError:
                console.print("  [red]Please enter a number[/]")
                return (raw, False)
        except (KeyboardInterrupt, EOFError):
            return ("", False)

    def _collect_plain(self) -> tuple[str, bool]:
        """Collect using plain text choice display."""
        try:
            print(f"\n  {self.label}")
            for i, (value, desc) in enumerate(self.choices, 1):
                print(f"    {i}. {desc}")

            raw = input(f"  Select (1-{len(self.choices)}) [1]: ").strip() or "1"
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(self.choices):
                    value = self.choices[idx][0]
                    result = self.validate(value)
                    if result.is_valid:
                        return (result.sanitized_value, True)
                    print(f"  Error: {result.error_message}")
                    return (value, False)
                print(f"  Invalid choice: {raw}")
                return (raw, False)
            except ValueError:
                print("  Please enter a number")
                return (raw, False)
        except (KeyboardInterrupt, EOFError):
            return ("", False)


# ── Confirmation Prompt ──────────────────────────────────────


class ConfirmPrompt(BasePrompt):
    """Yes/No confirmation prompt."""

    def __init__(self, field_name: str, label: str, default: bool = True) -> None:
        super().__init__(field_name, label, required=False, default="y" if default else "n")

    def collect(self) -> tuple[str, bool]:
        """Collect yes/no confirmation."""
        default_hint = "Y/n" if self.default == "y" else "y/N"
        try:
            raw = input(f"  {self.label} [{default_hint}]: ").strip().lower()
            if not raw:
                raw = self.default
            return ("yes" if raw in ("y", "yes") else "no", True)
        except (KeyboardInterrupt, EOFError):
            return ("no", False)


# ── Prompt Builder ───────────────────────────────────────────


class PromptBuilder:
    """Builder for composing multi-field prompt sessions.

    Collects multiple prompts into a single session and
    runs them sequentially with retry-on-validation-failure.

    Usage::

        builder = PromptBuilder()
        builder.add_text("username", "Username", validator=validate_username)
        builder.add_text("email", "Email", validator=validate_email)
        builder.add_choice("tier", "Select tier", choices=[
            ("starter", "Starter - $29/mo"),
            ("business", "Business - $99/mo"),
            ("enterprise", "Enterprise - $299/mo"),
        ])
        result = builder.run()
        if result:
            username = result.get("username")
    """

    MAX_RETRIES: int = 3

    def __init__(self, title: str = "") -> None:
        self._title = title
        self._prompts: list[BasePrompt] = []

    @property
    def title(self) -> str:
        return self._title

    def add_text(
        self,
        field_name: str,
        label: str,
        validator: Callable[[str], ValidationResult] | None = None,
        default: str = "",
        required: bool = True,
        mask: bool = False,
    ) -> PromptBuilder:
        """Add a text input prompt (fluent API)."""
        self._prompts.append(TextPrompt(field_name, label, validator, default, required, mask))
        return self

    def add_choice(
        self, field_name: str, label: str, choices: list[tuple[str, str]], default: str = "", required: bool = True
    ) -> PromptBuilder:
        """Add a multiple-choice prompt (fluent API)."""
        self._prompts.append(ChoicePrompt(field_name, label, choices, default=default, required=required))
        return self

    def add_confirm(self, field_name: str, label: str, default: bool = True) -> PromptBuilder:
        """Add a yes/no confirmation prompt (fluent API)."""
        self._prompts.append(ConfirmPrompt(field_name, label, default=default))
        return self

    def run(self) -> PromptResult:
        """Run all prompts sequentially with retry on validation failure.

        Returns:
            PromptResult with collected values or cancellation status.
        """
        result = PromptResult()

        # Display title
        if self._title:
            if HAS_RICH:
                console = Console()
                console.print(Panel(f"[bold]{self._title}[/]", border_style="cyan"))
            else:
                print(f"\n{'='*50}")
                print(f"  {self._title}")
                print(f"{'='*50}\n")

        # Collect each prompt
        for prompt in self._prompts:
            value = ""
            valid = False
            attempts = 0

            while not valid and attempts < self.MAX_RETRIES:
                value, valid = prompt.collect()
                attempts += 1

                if not valid and attempts < self.MAX_RETRIES:
                    if HAS_RICH:
                        Console().print(f"  [yellow]Retry {attempts}/{self.MAX_RETRIES}[/]")
                    else:
                        print(f"  Retry {attempts}/{self.MAX_RETRIES}")

                if not value and not prompt.required:
                    valid = True

            if not valid:
                result.errors.append(f"Failed to collect valid input for '{prompt.label}'")
                result.cancelled = True
                return result

            result.values[prompt.field_name] = value

        return result


# ── Pre-built Prompt Sessions ────────────────────────────────


def prompt_registration() -> PromptResult:
    """Pre-built registration prompt session."""
    from .validators.user_input import validate_email, validate_username

    return (
        PromptBuilder(title="Zenic-Agents Registration")
        .add_text("username", "Username", validator=validate_username, required=True)
        .add_text("email", "Email address", validator=validate_email, required=True)
        .add_text("device_name", "Device name", default="My Device", required=False)
        .add_choice(
            "tier",
            "Select your plan",
            choices=[
                ("starter", "Starter — $29/mo USDT TRC20"),
                ("business", "Business — $99/mo USDT TRC20 (14-day trial)"),
                ("enterprise", "Enterprise — $299/mo USDT TRC20"),
                ("on_premise_enterprise", "On-Premise — $799/mo + $2,000 setup"),
            ],
            default="starter",
        )
        .run()
    )


def prompt_activation() -> PromptResult:
    """Pre-built activation prompt session."""
    from .validators.activation_key import validate_activation_key

    return (
        PromptBuilder(title="License Activation")
        .add_text("key", "Activation Key (ZENIC-XXXX-XXXX-XXXX-XXXX)", validator=validate_activation_key, required=True)
        .add_text("username", "Registered username", required=False)
        .run()
    )
