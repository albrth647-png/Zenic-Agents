"""
ZENIC-AGENTS — Auth Utilities.

JWT token creation/verification and password hashing.
Uses PyJWT for tokens and stdlib hashlib for passwords.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

# ── Configuration ──────────────────────────────────────────────

JWT_SECRET: str = os.environ.get("ZENIC_AGENTS_JWT_SECRET", "")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)
    import logging
    logging.getLogger(__name__).warning(
        "ZENIC_AGENTS_JWT_SECRET not set — using auto-generated secret. "
        "All tokens will be invalidated on restart. "
        "Set this env var for persistent tokens."
    )
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_HOURS: int = 24

# ── JWT ────────────────────────────────────────────────────────


def create_access_token(data: dict) -> str:
    """Create a JWT access token with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises on invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── Password Hashing (PBKDF2-HMAC-SHA256) ──────────────────────

_SALT_LENGTH: int = 32
_ITERATIONS: int = 600_000
_KEY_LENGTH: int = 32  # 256 bits


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256. Returns hex string: salt$hash."""
    salt = secrets.token_hex(_SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
        dklen=_KEY_LENGTH,
    )
    return f"{salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a PBKDF2 hash string."""
    try:
        salt, stored_hash = hashed.split("$", 1)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            _ITERATIONS,
            dklen=_KEY_LENGTH,
        )
        return secrets.compare_digest(dk.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False
