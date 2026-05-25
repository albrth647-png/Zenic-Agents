"""
Zenic-Agents — Onboarding Validators Package (Phase 10)

Chain-of-responsibility validation for user inputs during onboarding:
activation keys, confirmation codes, usernames, emails, and payment refs.

Design Patterns:
  - Chain of Responsibility: ValidationResult + composed validator chains
  - Strategy: pluggable validation strategies per field type
  - Null Object: ValidResult / InvalidResult for monoidal composition
"""

from .activation_key import (
    ActivationKeyValidator,
    ConfirmationCodeValidator,
    validate_activation_key,
    validate_confirmation_code,
    ACTIVATION_KEY_PATTERN,
    CONFIRMATION_CODE_PATTERN,
)
from .user_input import (
    UsernameValidator,
    EmailValidator,
    PaymentRefValidator,
    validate_username,
    validate_email,
    validate_payment_ref,
    ValidationResult,
    ValidResult,
    InvalidResult,
    ValidatorChain,
)

__all__ = [
    # Activation key validators
    "ActivationKeyValidator",
    "ConfirmationCodeValidator",
    "validate_activation_key",
    "validate_confirmation_code",
    "ACTIVATION_KEY_PATTERN",
    "CONFIRMATION_CODE_PATTERN",
    # User input validators
    "UsernameValidator",
    "EmailValidator",
    "PaymentRefValidator",
    "validate_username",
    "validate_email",
    "validate_payment_ref",
    # Core validation types
    "ValidationResult",
    "ValidResult",
    "InvalidResult",
    "ValidatorChain",
]
