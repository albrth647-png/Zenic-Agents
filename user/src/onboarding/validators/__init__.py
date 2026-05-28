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
    ACTIVATION_KEY_PATTERN,
    CONFIRMATION_CODE_PATTERN,
    ActivationKeyValidator,
    ConfirmationCodeValidator,
    validate_activation_key,
    validate_confirmation_code,
)
from .user_input import (
    EmailValidator,
    InvalidResult,
    PaymentRefValidator,
    UsernameValidator,
    ValidationResult,
    ValidatorChain,
    ValidResult,
    validate_email,
    validate_payment_ref,
    validate_username,
)

__all__ = [
    "ACTIVATION_KEY_PATTERN",
    "CONFIRMATION_CODE_PATTERN",
    # Activation key validators
    "ActivationKeyValidator",
    "ConfirmationCodeValidator",
    "EmailValidator",
    "InvalidResult",
    "PaymentRefValidator",
    # User input validators
    "UsernameValidator",
    "ValidResult",
    # Core validation types
    "ValidationResult",
    "ValidatorChain",
    "validate_activation_key",
    "validate_confirmation_code",
    "validate_email",
    "validate_payment_ref",
    "validate_username",
]
