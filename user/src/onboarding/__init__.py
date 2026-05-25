"""
Zenic-Agents — User Onboarding TUI Package (Phase 10)

End-user onboarding system for Zenic-Agents v3.0.0.
Provides registration, license activation (ZENIC-xxxx keys),
confirmation code display (CONF-xxxxxxxx), status checking,
and hardware fingerprint display.

Architecture:
  - OnboardingTUI:     Facade / entry point
  - flows/             Template Method-based onboarding flows
  - validators/        Chain-of-responsibility input validation
  - renderers/         Rich-based display components
  - prompts/           Interactive input collection
  - cli.py:            argparse-based CLI entry point

Design Patterns:
  - Facade:        OnboardingTUI simplifies the subsystem
  - Template Method: BaseFlow defines the algorithm skeleton
  - Strategy:      Pluggable activation strategies (online/offline)
  - Chain of Responsibility: Validator chains for input validation
  - Builder:       PromptBuilder and RegistrationDataBuilder
  - Registry:      FlowRegistry for flow discovery
  - Command:       Each CLI command is an executable command
  - State Machine: OnboardingState / FlowState lifecycle tracking
  - Null Object:   ValidResult / InvalidResult for monoidal composition
  - Newtype:       ActivationKey / ConfirmationCode semantic wrappers
  - Observer:      Progress step-change callbacks

Usage (Python API)::

    from src.onboarding import OnboardingTUI
    app = OnboardingTUI()
    app.show_welcome()
    result = app.register(username="user", email="user@example.com")
    result = app.activate(key="ZENIC-XXXX-XXXX-XXXX-XXXX")
    status = app.check_status()

Usage (CLI)::

    zenic-onboard welcome
    zenic-onboard register -u USER -e EMAIL
    zenic-onboard activate -k ZENIC-XXXX-XXXX-XXXX-XXXX
    zenic-onboard status
    zenic-onboard hardware
    zenic-onboard quickstart
"""

from .app import OnboardingTUI, OnboardingState
from .flows import (
    BaseFlow, FlowState, FlowResult, FlowContext, FlowRegistry,
    RegistrationFlow, RegistrationData,
    ActivationFlow, ActivationResult,
    StatusFlow, StatusResult,
    HardwareFlow, HardwareResult,
)
from .validators import (
    ActivationKeyValidator, ConfirmationCodeValidator,
    validate_activation_key, validate_confirmation_code,
    UsernameValidator, EmailValidator, PaymentRefValidator,
    validate_username, validate_email, validate_payment_ref,
    ValidationResult, ValidResult, InvalidResult, ValidatorChain,
)
from .renderers import (
    WelcomeRenderer, render_welcome,
    StatusRenderer, render_status_panel,
    ProgressRenderer, StepIndicator, render_progress,
)
from .prompts import (
    PromptBuilder, PromptResult,
    prompt_registration, prompt_activation,
)
from .cli import main as cli_main, VERSION

__all__ = [
    # Facade
    "OnboardingTUI",
    "OnboardingState",
    # Flows
    "BaseFlow",
    "FlowState",
    "FlowResult",
    "FlowContext",
    "FlowRegistry",
    "RegistrationFlow",
    "RegistrationData",
    "ActivationFlow",
    "ActivationResult",
    "StatusFlow",
    "StatusResult",
    "HardwareFlow",
    "HardwareResult",
    # Validators
    "ActivationKeyValidator",
    "ConfirmationCodeValidator",
    "validate_activation_key",
    "validate_confirmation_code",
    "UsernameValidator",
    "EmailValidator",
    "PaymentRefValidator",
    "validate_username",
    "validate_email",
    "validate_payment_ref",
    "ValidationResult",
    "ValidResult",
    "InvalidResult",
    "ValidatorChain",
    # Renderers
    "WelcomeRenderer",
    "render_welcome",
    "StatusRenderer",
    "render_status_panel",
    "ProgressRenderer",
    "StepIndicator",
    "render_progress",
    # Prompts
    "PromptBuilder",
    "PromptResult",
    "prompt_registration",
    "prompt_activation",
    # CLI
    "cli_main",
    "VERSION",
]
