"""
Zenic-Agents — Activation Key & Confirmation Code Validators (Phase 10)

Validates ZENIC-xxx activation keys and CONF-xxx confirmation codes
using constant-time comparison semantics and format enforcement.

Key Format:  ZENIC-XXXX-XXXX-XXXX-XXXX  (4 groups of 4 alphanumeric)
Conf Format: CONF-XXXXXXXX              (8 alphanumeric)

Design Patterns:
  - Strategy: each validator encapsulates a single validation strategy
  - Template Method: _validate_format() → _validate_checksum() → _validate_semantics()
  - Newtype: ActivationKey / ConfirmationCode as semantic string wrappers
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from typing import ClassVar, Final, List, Optional, Tuple

# ── Constants ────────────────────────────────────────────────

ACTIVATION_KEY_PATTERN: Final[str] = r"^ZENIC-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
CONFIRMATION_CODE_PATTERN: Final[str] = r"^CONF-[A-Z0-9]{8}$"

_CHECKSUM_ALPHABET: Final[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_HMAC_KEY_ENV: Final[str] = "ZENIC_VALIDATION_HMAC_KEY"


# ── Newtypes ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ActivationKey:
    """Semantic wrapper for a validated ZENIC-xxxx activation key.

    Can only be constructed via ``ActivationKey.parse()`` which enforces
    the full format + checksum validation pipeline.
    """
    value: str

    @classmethod
    def parse(cls, raw: str) -> "ActivationKey":
        """Parse and validate a raw activation key string.

        Raises:
            ValueError: If format or checksum validation fails.
        """
        validator = ActivationKeyValidator()
        result = validator.validate(raw)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return cls(value=raw.upper().strip())

    @property
    def groups(self) -> Tuple[str, str, str, str]:
        """Extract the 4 alphanumeric groups from the key."""
        parts = self.value.split("-")
        return (parts[1], parts[2], parts[3], parts[4])

    def masked(self) -> str:
        """Return the key with groups 2-3 masked for display: ZENIC-ABCD-****-****-WXYZ"""
        g = self.groups
        return f"ZENIC-{g[0]}-****-****-{g[3]}"


@dataclass(frozen=True, slots=True)
class ConfirmationCode:
    """Semantic wrapper for a validated CONF-xxxxxxxx confirmation code."""
    value: str

    @classmethod
    def parse(cls, raw: str) -> "ConfirmationCode":
        """Parse and validate a raw confirmation code string."""
        validator = ConfirmationCodeValidator()
        result = validator.validate(raw)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return cls(value=raw.upper().strip())

    def constant_time_eq(self, other: str) -> bool:
        """Compare against another code in constant time to prevent timing attacks."""
        return hmac.compare_digest(self.value.upper().strip(), other.upper().strip())


# ── Validation Result (local, reused from user_input) ────────

from .user_input import ValidationResult, ValidResult, InvalidResult


# ── Activation Key Validator ─────────────────────────────────

class ActivationKeyValidator:
    """Multi-stage validator for ZENIC-xxxx activation keys.

    Validation pipeline (Template Method):
      1. _validate_format()     — regex pattern match
      2. _validate_checksum()   — last group is CRC of first 3 groups
      3. _validate_semantics()  — no all-zeros groups, no trivial patterns

    Usage::

        validator = ActivationKeyValidator()
        result = validator.validate("ZENIC-AB12-CD34-EF56-GH78")
        if result.is_valid:
            key = ActivationKey.parse(result.sanitized_value)
    """

    _PATTERN: ClassVar[re.Pattern[str]] = re.compile(ACTIVATION_KEY_PATTERN)

    def validate(self, raw: str) -> ValidationResult:
        """Run the full validation pipeline on a raw key string."""
        sanitized = raw.upper().strip()

        # Stage 1: Format
        fmt_result = self._validate_format(sanitized)
        if not fmt_result.is_valid:
            return fmt_result

        # Stage 2: Checksum
        csum_result = self._validate_checksum(sanitized)
        if not csum_result.is_valid:
            return csum_result

        # Stage 3: Semantics
        sem_result = self._validate_semantics(sanitized)
        if not sem_result.is_valid:
            return sem_result

        return ValidResult(sanitized_value=sanitized)

    def _validate_format(self, key: str) -> ValidationResult:
        """Stage 1: Verify the key matches ZENIC-XXXX-XXXX-XXXX-XXXX."""
        if not key:
            return InvalidResult("Activation key is empty")
        if not self._PATTERN.match(key):
            return InvalidResult(
                f"Invalid activation key format. Expected: ZENIC-XXXX-XXXX-XXXX-XXXX, got: {key[:20]}"
            )
        return ValidResult(sanitized_value=key)

    def _validate_checksum(self, key: str) -> ValidationResult:
        """Stage 2: Verify the last group is a checksum of the first 3 groups.

        The checksum is computed as: CRC32(first3groups) mod 36^4,
        mapped to 4 characters from the alphanumeric alphabet.
        This is deterministic — same key always produces same checksum.
        """
        parts = key.split("-")
        data_groups = parts[1:4]  # First 3 data groups
        check_group = parts[4]    # Last group is checksum

        combined = "".join(data_groups)
        # Deterministic hash-based checksum
        digest = hashlib.sha256(combined.encode()).digest()
        # Take first 3 bytes as numeric seed
        seed = int.from_bytes(digest[:3], "big")
        expected = ""
        for i in range(4):
            idx = (seed >> (6 * i)) & 0x3F
            expected += _CHECKSUM_ALPHABET[idx % len(_CHECKSUM_ALPHABET)]

        if not hmac.compare_digest(check_group, expected):
            return InvalidResult(
                "Activation key checksum mismatch — key may be corrupted or mistyped"
            )
        return ValidResult(sanitized_value=key)

    def _validate_semantics(self, key: str) -> ValidationResult:
        """Stage 3: Reject trivial / test patterns.

        Blocks:
          - All zeros in any group (ZENIC-0000-...)
          - All same character (ZENIC-AAAA-...)
          - Sequential patterns (ZENIC-1234-...)
        """
        parts = key.split("-")[1:]  # Skip ZENIC prefix
        for i, group in enumerate(parts):
            # All same character
            if len(set(group)) == 1:
                # Allow in the checksum position only if it's valid
                if i < 3:
                    return InvalidResult(
                        f"Group {i+1} contains all identical characters — invalid key"
                    )
            # All zeros
            if group == "0000" and i < 3:
                return InvalidResult(
                    f"Group {i+1} is all zeros — invalid key"
                )
            # Sequential (1234, ABCD)
            if group in ("1234", "ABCD", "4321", "DCBA") and i < 3:
                return InvalidResult(
                    f"Group {i+1} is a sequential pattern — invalid key"
                )
        return ValidResult(sanitized_value=key)


# ── Confirmation Code Validator ──────────────────────────────

class ConfirmationCodeValidator:
    """Validator for CONF-xxxxxxxx confirmation codes.

    These codes are generated by the admin after activation and must
    be displayed to the user for verification.
    """

    _PATTERN: ClassVar[re.Pattern[str]] = re.compile(CONFIRMATION_CODE_PATTERN)

    def validate(self, raw: str) -> ValidationResult:
        """Validate a confirmation code string."""
        sanitized = raw.upper().strip()

        if not sanitized:
            return InvalidResult("Confirmation code is empty")

        if not self._PATTERN.match(sanitized):
            return InvalidResult(
                f"Invalid confirmation code format. Expected: CONF-XXXXXXXX, got: {sanitized[:15]}"
            )

        # Semantic: the 8-char payload must not be all same character
        payload = sanitized.split("-")[1]
        if len(set(payload)) == 1:
            return InvalidResult("Confirmation code contains all identical characters")

        return ValidResult(sanitized_value=sanitized)


# ── Convenience Functions ────────────────────────────────────

def validate_activation_key(raw: str) -> ValidationResult:
    """One-shot validation of a ZENIC-xxxx activation key."""
    return ActivationKeyValidator().validate(raw)


def validate_confirmation_code(raw: str) -> ValidationResult:
    """One-shot validation of a CONF-xxxxxxxx confirmation code."""
    return ConfirmationCodeValidator().validate(raw)


# ── Key Generation (Admin-side, for testing) ────────────────

def generate_activation_key() -> str:
    """Generate a valid ZENIC-xxxx activation key with correct checksum.

    This is intended for admin/testing use only. The production
    key generation happens in the Rust zenic-license crate.
    """
    # Generate 3 random data groups
    groups: List[str] = []
    for _ in range(3):
        group = "".join(secrets.choice(_CHECKSUM_ALPHABET) for _ in range(4))
        groups.append(group)

    combined = "".join(groups)
    digest = hashlib.sha256(combined.encode()).digest()
    seed = int.from_bytes(digest[:3], "big")
    check = ""
    for i in range(4):
        idx = (seed >> (6 * i)) & 0x3F
        check += _CHECKSUM_ALPHABET[idx % len(_CHECKSUM_ALPHABET)]

    return f"ZENIC-{groups[0]}-{groups[1]}-{groups[2]}-{check}"


def generate_confirmation_code() -> str:
    """Generate a CONF-xxxxxxxx confirmation code."""
    payload = "".join(secrets.choice(_CHECKSUM_ALPHABET) for _ in range(8))
    return f"CONF-{payload}"
