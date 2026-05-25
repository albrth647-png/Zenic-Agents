"""
Zenic-Agents — License Management Package (Admin)

Tools for admin to create, list, revoke, and manage licenses.

Key distinction from user-side license module:
  - user/src/core/license/ = License validation, verification, hardware binding
  - admin/license_mgmt/   = License creation, bulk operations, revocation, auditing

Components:
  - ManagedLicense: Data type for a license managed by admin
  - AdminLicenseDB: Persistent SQLite storage for admin-managed licenses
  - LicenseManagerCLI: CLI for full license lifecycle management
"""

from __future__ import annotations

from .license_manager_cli import (
    AdminLicenseDB,
    LicenseManagerCLI,
    ManagedLicense,
)

__all__: list[str] = [
    "ManagedLicense",
    "AdminLicenseDB",
    "LicenseManagerCLI",
]
