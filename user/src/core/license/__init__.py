"""
Zenic-Agents Asistente - License Package (Phase 6.3)

Cryptographic licensing system with ECDSA signing, hardware binding,
NTP time verification, remote kill switch, and heartbeat.

Components:
- LicenseManager: Central license lifecycle management
- ECDSASigner: ECDSA/HMAC signing and verification
- LicenseInfo, LicenseStatus, LicenseTier: License data types
- KillSwitchStatus: Remote kill switch state
"""

from .manager import (
    LicenseManager,
    get_license_manager,
    reset_license_manager,
)
from .signer import (
    ECDSASigner,
    get_signer,
    sign_data,
    verify_signature,
)
from .types import (
    HardwareBindingStrength,
    KillSwitchStatus,
    LicenseInfo,
    LicenseStatus,
    LicenseTier,
    LicenseVerificationResult,
)

__all__ = [
    # Signer
    "ECDSASigner",
    "HardwareBindingStrength",
    "KillSwitchStatus",
    "LicenseInfo",
    # Manager
    "LicenseManager",
    "LicenseStatus",
    # Types
    "LicenseTier",
    "LicenseVerificationResult",
    "get_license_manager",
    "get_signer",
    "reset_license_manager",
    "sign_data",
    "verify_signature",
]
