"""
Zenic-Agents — Firebase Admin Package

Tools for admin to process activation requests received via Firebase.
The user sends activation requests via OnlineActivationStrategy,
and the admin can list, approve, or reject them here.

Components:
  - ActivationRequest: Data type for a user activation request
  - FirebaseConfig: Firebase Realtime DB configuration for admin access
  - ActivationRequestProcessor: List and process incoming activation requests
"""

from __future__ import annotations

from .activation_processor import (
    ActivationRequest,
    ActivationRequestProcessor,
    FirebaseConfig,
)

__all__: list[str] = [
    "ActivationRequest",
    "FirebaseConfig",
    "ActivationRequestProcessor",
]
