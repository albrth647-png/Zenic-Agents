"""
Zenic-Agents — User Input Validators (Phase 10)

General-purpose validation for user inputs during onboarding:
usernames, emails, USDT TRC20 payment references.

Provides the core ValidationResult types used across the entire
onboarding validator subsystem.

Design Patterns:
  - Chain of Responsibility: ValidatorChain composes multiple validators
  - Null Object: ValidResult / InvalidResult as monoidal result types
  - Strategy: each validator is a pluggable strategy
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Final

# ── Core Validation Result Types ─────────────────────────────


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Base class for validation results — supports monoidal composition.

    A validation result is either valid (green path) or invalid (red path).
    This is a sealed hierarchy: only ValidResult and InvalidResult exist.

    Composition rule (monoid):
        ValidResult + ValidResult   = ValidResult
        ValidResult + InvalidResult = InvalidResult
        InvalidResult + any         = InvalidResult  (short-circuit)
    """

    is_valid: bool
    error_message: str = ""
    sanitized_value: str = ""

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Compose two validation results (monoidal AND)."""
        if not self.is_valid:
            return self
        if not other.is_valid:
            return other
        return ValidResult(sanitized_value=other.sanitized_value or self.sanitized_value)

    def __bool__(self) -> bool:
        return self.is_valid


@dataclass(frozen=True, slots=True)
class ValidResult(ValidationResult):
    """Successful validation — the input passes all checks."""

    is_valid: bool = True
    error_message: str = ""
    sanitized_value: str = ""


@dataclass(frozen=True, slots=True)
class InvalidResult(ValidationResult):
    """Failed validation — the input violates one or more rules."""

    is_valid: bool = False
    error_message: str = "Validation failed"
    sanitized_value: str = ""


# ── Abstract Validator ───────────────────────────────────────


class BaseValidator(ABC):
    """Abstract base for all validators (Strategy pattern).

    Subclasses implement ``validate()`` which returns a ValidationResult.
    Validators are composable via ``ValidatorChain``.
    """

    @abstractmethod
    def validate(self, raw: str) -> ValidationResult:
        """Validate a raw string input and return a result."""
        ...

    def __call__(self, raw: str) -> ValidationResult:
        """Allow validator to be used as a callable."""
        return self.validate(raw)


# ── Validator Chain (Chain of Responsibility) ────────────────


class ValidatorChain:
    """Compose multiple validators into a sequential chain.

    Each validator runs in order. If any returns InvalidResult,
    the chain short-circuits and returns that failure.

    Usage::

        chain = ValidatorChain()
        chain.add(FormatValidator())
        chain.add(LengthValidator(min_len=3, max_len=32))
        chain.add(ReservedWordValidator())
        result = chain.validate("my_username")
    """

    def __init__(self, name: str = "unnamed") -> None:
        self._validators: list[BaseValidator] = []
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def validator_count(self) -> int:
        return len(self._validators)

    def add(self, validator: BaseValidator) -> ValidatorChain:
        """Add a validator to the chain (fluent API)."""
        self._validators.append(validator)
        return self

    def validate(self, raw: str) -> ValidationResult:
        """Run all validators in sequence, short-circuiting on first failure."""
        result: ValidationResult = ValidResult(sanitized_value=raw.strip())
        for validator in self._validators:
            result = result.merge(validator.validate(raw))
            if not result.is_valid:
                return result
        return result

    def __call__(self, raw: str) -> ValidationResult:
        return self.validate(raw)


# ── Username Validator ───────────────────────────────────────

_RESERVED_USERNAMES: Final[tuple] = (
    "admin",
    "root",
    "system",
    "zenic",
    "support",
    "help",
    "null",
    "undefined",
    "test",
    "guest",
    "anonymous",
    "moderator",
    "mod",
    "superuser",
    "su",
)

_USERNAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{2,31}$", re.IGNORECASE)


class _UsernameFormatValidator(BaseValidator):
    """Username must start with a letter, contain only a-z, 0-9, _."""

    def validate(self, raw: str) -> ValidationResult:
        sanitized = raw.strip()
        if not sanitized:
            return InvalidResult("Username cannot be empty")
        if not _USERNAME_PATTERN.match(sanitized):
            return InvalidResult(
                "Username must start with a letter and contain only " "letters, digits, and underscores (3-32 chars)"
            )
        return ValidResult(sanitized_value=sanitized)


class _UsernameReservedValidator(BaseValidator):
    """Username must not be a reserved system name."""

    def validate(self, raw: str) -> ValidationResult:
        lower = raw.strip().lower()
        if lower in _RESERVED_USERNAMES:
            return InvalidResult(f"Username '{lower}' is reserved and cannot be used")
        return ValidResult(sanitized_value=raw.strip())


class _UsernameLengthValidator(BaseValidator):
    """Username length enforcement."""

    def __init__(self, min_len: int = 3, max_len: int = 32) -> None:
        self._min = min_len
        self._max = max_len

    def validate(self, raw: str) -> ValidationResult:
        sanitized = raw.strip()
        length = len(sanitized)
        if length < self._min:
            return InvalidResult(f"Username too short ({length} chars, minimum {self._min})")
        if length > self._max:
            return InvalidResult(f"Username too long ({length} chars, maximum {self._max})")
        return ValidResult(sanitized_value=sanitized)


class UsernameValidator:
    """Facade for username validation with pre-built validator chain.

    Uses the Chain of Responsibility pattern internally:
    Format → Reserved → Length

    Usage::

        validator = UsernameValidator()
        result = validator.validate("yurislay9")
        if result:
            username = result.sanitized_value
    """

    def __init__(self, min_len: int = 3, max_len: int = 32) -> None:
        self._chain = ValidatorChain(name="username")
        self._chain.add(_UsernameFormatValidator())
        self._chain.add(_UsernameReservedValidator())
        self._chain.add(_UsernameLengthValidator(min_len=min_len, max_len=max_len))

    def validate(self, raw: str) -> ValidationResult:
        return self._chain.validate(raw)

    def __call__(self, raw: str) -> ValidationResult:
        return self.validate(raw)


# ── Email Validator ──────────────────────────────────────────

_EMAIL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

_DISPOSABLE_DOMAINS: Final[frozenset] = frozenset(
    {
        "tempmail.com",
        "throwaway.email",
        "guerrillamail.com",
        "mailinator.com",
        "yopmail.com",
        "sharklasers.com",
        "guerrillamailblock.com",
        "grr.la",
        "dispostable.com",
        "trashmail.com",
        "10minutemail.com",
    }
)


class _EmailFormatValidator(BaseValidator):
    """Basic email format validation via regex."""

    def validate(self, raw: str) -> ValidationResult:
        sanitized = raw.strip()
        if not sanitized:
            return InvalidResult("Email cannot be empty")
        if not _EMAIL_PATTERN.match(sanitized):
            return InvalidResult(f"Invalid email format: {sanitized}")
        return ValidResult(sanitized_value=sanitized)


class _EmailDisposableValidator(BaseValidator):
    """Block known disposable email domains."""

    def validate(self, raw: str) -> ValidationResult:
        sanitized = raw.strip().lower()
        domain = sanitized.split("@")[-1] if "@" in sanitized else ""
        if domain in _DISPOSABLE_DOMAINS:
            return InvalidResult(
                f"Disposable email domain '{domain}' is not allowed. " "Please use a permanent email address."
            )
        return ValidResult(sanitized_value=raw.strip())


class _EmailLengthValidator(BaseValidator):
    """Email total length enforcement."""

    def __init__(self, max_len: int = 254) -> None:
        self._max = max_len

    def validate(self, raw: str) -> ValidationResult:
        if len(raw.strip()) > self._max:
            return InvalidResult(f"Email too long (maximum {self._max} characters)")
        return ValidResult(sanitized_value=raw.strip())


class EmailValidator:
    """Facade for email validation with pre-built validator chain.

    Chain: Format → Disposable → Length
    """

    def __init__(self, max_len: int = 254) -> None:
        self._chain = ValidatorChain(name="email")
        self._chain.add(_EmailFormatValidator())
        self._chain.add(_EmailDisposableValidator())
        self._chain.add(_EmailLengthValidator(max_len=max_len))

    def validate(self, raw: str) -> ValidationResult:
        return self._chain.validate(raw)


# ── Payment Reference Validator ──────────────────────────────

_TRC20_ADDRESS_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^T[A-Za-z1-9]{33}$")

_TX_HASH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-fA-F0-9]{64}$")


class _PaymentFormatValidator(BaseValidator):
    """Validate USDT TRC20 payment reference format.

    Accepts either:
      - TRC20 wallet address: T + 33 alphanumeric chars
      - Transaction hash: 64 hex chars
    """

    def validate(self, raw: str) -> ValidationResult:
        sanitized = raw.strip()
        if not sanitized:
            return InvalidResult("Payment reference cannot be empty")

        if _TRC20_ADDRESS_PATTERN.match(sanitized):
            return ValidResult(sanitized_value=sanitized)

        if _TX_HASH_PATTERN.match(sanitized):
            return ValidResult(sanitized_value=sanitized)

        return InvalidResult(
            "Invalid payment reference. Expected either:\n"
            "  - TRC20 wallet address (T + 33 alphanumeric chars)\n"
            "  - Transaction hash (64 hex characters)"
        )


class _PaymentLengthValidator(BaseValidator):
    """Payment reference length enforcement."""

    def validate(self, raw: str) -> ValidationResult:
        length = len(raw.strip())
        if length < 34:
            return InvalidResult(f"Payment reference too short ({length} chars)")
        if length > 64:
            return InvalidResult(f"Payment reference too long ({length} chars)")
        return ValidResult(sanitized_value=raw.strip())


class PaymentRefValidator:
    """Facade for USDT TRC20 payment reference validation.

    Chain: Format → Length
    """

    def __init__(self) -> None:
        self._chain = ValidatorChain(name="payment_ref")
        self._chain.add(_PaymentFormatValidator())
        self._chain.add(_PaymentLengthValidator())

    def validate(self, raw: str) -> ValidationResult:
        return self._chain.validate(raw)


# ── Convenience Functions ────────────────────────────────────


def validate_username(raw: str) -> ValidationResult:
    """One-shot username validation."""
    return UsernameValidator().validate(raw)


def validate_email(raw: str) -> ValidationResult:
    """One-shot email validation."""
    return EmailValidator().validate(raw)


def validate_payment_ref(raw: str) -> ValidationResult:
    """One-shot USDT TRC20 payment reference validation."""
    return PaymentRefValidator().validate(raw)
