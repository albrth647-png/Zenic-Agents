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

from .app import OnboardingState, OnboardingTUI
from .cli import VERSION
from .cli import main as cli_main
from .flows import (
    ActivationFlow,
    ActivationResult,
    BaseFlow,
    FlowContext,
    FlowRegistry,
    FlowResult,
    FlowState,
    HardwareFlow,
    HardwareResult,
    RegistrationData,
    RegistrationFlow,
    StatusFlow,
    StatusResult,
)
from .prompts import (
    PromptBuilder,
    PromptResult,
    prompt_activation,
    prompt_registration,
)
from .renderers import (
    ProgressRenderer,
    StatusRenderer,
    StepIndicator,
    WelcomeRenderer,
    render_progress,
    render_status_panel,
    render_welcome,
)
from .validators import (
    ActivationKeyValidator,
    ConfirmationCodeValidator,
    EmailValidator,
    InvalidResult,
    PaymentRefValidator,
    UsernameValidator,
    ValidationResult,
    ValidatorChain,
    ValidResult,
    validate_activation_key,
    validate_confirmation_code,
    validate_email,
    validate_payment_ref,
    validate_username,
)

__all__ = [
    "VERSION",
    "ActivationFlow",
    # Validators
    "ActivationKeyValidator",
    "ActivationResult",
    # Flows
    "BaseFlow",
    "ConfirmationCodeValidator",
    "EmailValidator",
    "FlowContext",
    "FlowRegistry",
    "FlowResult",
    "FlowState",
    "HardwareFlow",
    "HardwareResult",
    "InvalidResult",
    "OnboardingState",
    # Facade
    "OnboardingTUI",
    "PaymentRefValidator",
    "ProgressRenderer",
    # Prompts
    "PromptBuilder",
    "PromptResult",
    "RegistrationData",
    "RegistrationFlow",
    "StatusFlow",
    "StatusRenderer",
    "StatusResult",
    "StepIndicator",
    "UsernameValidator",
    "ValidResult",
    "ValidationResult",
    "ValidatorChain",
    # Renderers
    "WelcomeRenderer",
    # CLI
    "cli_main",
    "prompt_activation",
    "prompt_registration",
    "render_progress",
    "render_status_panel",
    "render_welcome",
    "validate_activation_key",
    "validate_confirmation_code",
    "validate_email",
    "validate_payment_ref",
    "validate_username",
]
