"""
Zenic-Agents — Admin Key Generator

Generates ZENIC-xxx activation keys and CONF-xxx confirmation codes.
This is the admin-side tool for creating license keys.

Design Patterns:
  - Strategy: different key generation algorithms
  - Factory: creates keys with correct checksums

Key Format:  ZENIC-XXXX-XXXX-XXXX-XXXX  (4 groups of 4 alphanumeric)
Conf Format: CONF-XXXXXXXX              (8 alphanumeric)
"""

from __future__ import annotations

import hashlib
import secrets

# ── Constants ────────────────────────────────────────────────

_CHECKSUM_ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# ── Key Generation ────────────────────────────────────────


def generate_activation_key() -> str:
    """Generate a valid ZENIC-xxxx activation key with correct checksum.

    This is intended for admin/testing use only. The production
    key generation happens in the Rust zenic-license crate.

    Returns:
        A valid activation key string in format ZENIC-XXXX-XXXX-XXXX-XXXX
    """
    # Generate 3 random data groups
    groups: list[str] = []
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
    """Generate a CONF-xxxxxxxx confirmation code.

    Returns:
        A valid confirmation code string in format CONF-XXXXXXXX
    """
    payload = "".join(secrets.choice(_CHECKSUM_ALPHABET) for _ in range(8))
    return f"CONF-{payload}"


def generate_bulk_keys(count: int = 10) -> list[dict[str, str]]:
    """Generate multiple activation keys at once.

    Args:
        count: Number of keys to generate (default: 10)

    Returns:
        List of dicts with 'activation_key' and 'confirmation_code'
    """
    keys = []
    for _ in range(count):
        keys.append({
            "activation_key": generate_activation_key(),
            "confirmation_code": generate_confirmation_code(),
        })
    return keys


# ── CLI Entry Point ─────────────────────────────────────────

def main():
    """Simple CLI for generating keys."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="zenic-keygen",
        description="Generate Zenic-Agents activation keys and confirmation codes",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=1,
        help="Number of keys to generate (default: 1)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--conf-only",
        action="store_true",
        help="Generate confirmation codes only",
    )
    parser.add_argument(
        "--activation-only",
        action="store_true",
        help="Generate activation keys only",
    )

    args = parser.parse_args()

    if args.conf_only:
        codes = [generate_confirmation_code() for _ in range(args.count)]
        if args.format == "json":
            import json
            print(json.dumps({"confirmation_codes": codes}, indent=2))
        elif args.format == "csv":
            for code in codes:
                print(f"CONFIRMATION,{code}")
        else:
            for code in codes:
                print(code)
        return

    if args.activation_only:
        keys = [generate_activation_key() for _ in range(args.count)]
        if args.format == "json":
            import json
            print(json.dumps({"activation_keys": keys}, indent=2))
        elif args.format == "csv":
            for key in keys:
                print(f"ACTIVATION,{key}")
        else:
            for key in keys:
                print(key)
        return

    keys = generate_bulk_keys(args.count)
    if args.format == "json":
        import json
        print(json.dumps({"keys": keys}, indent=2))
    elif args.format == "csv":
        for k in keys:
            print(f"ACTIVATION,{k['activation_key']}")
            print(f"CONFIRMATION,{k['confirmation_code']}")
    else:
        for i, k in enumerate(keys, 1):
            print(f"Key #{i}")
            print(f"  Activation:  {k['activation_key']}")
            print(f"  Confirmation: {k['confirmation_code']}")
            print()


if __name__ == "__main__":
    main()
