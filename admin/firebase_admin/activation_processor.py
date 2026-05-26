"""
Zenic-Agents — Firebase Activation Request Processor (Admin)

Processes incoming license activation requests from users via Firebase.
The admin can list pending requests, approve them (issuing a license),
or reject them.

Flow:
  1. User sends activation request via OnlineActivationStrategy → Firebase
  2. Admin polls/inspects pending requests here
  3. Admin approves → LicenseIssuer creates + signs a license
  4. Signed license is posted back to Firebase for the user to retrieve
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Data Types ───────────────────────────────────────────────


@dataclass
class ActivationRequest:
    """An activation request submitted by a user via Firebase."""

    request_id: str
    activation_key: str
    device_id: str
    username: str
    timestamp: float
    nonce: str
    status: str = "pending"  # pending | approved | rejected
    notes: str = ""


@dataclass
class FirebaseConfig:
    """Firebase Realtime DB configuration for admin access."""

    database_url: str
    service_account_key: str | None = None
    auth_secret: str | None = None

    @classmethod
    def from_env(cls) -> FirebaseConfig | None:
        """Load config from environment variables."""
        url = os.environ.get("ZENIC_FIREBASE_URL", "")
        if not url:
            return None
        return cls(
            database_url=url,
            service_account_key=os.environ.get("ZENIC_FIREBASE_SERVICE_ACCOUNT", ""),
            auth_secret=os.environ.get("ZENIC_FIREBASE_KEY", ""),
        )


# ── Activation Request Processor ─────────────────────────────


class ActivationRequestProcessor:
    """Admin tool to list, inspect, approve, and reject activation requests.

    Reads from the Firebase Realtime DB path ``/activation_requests``
    where the user-side ``OnlineActivationStrategy`` posts requests.
    """

    def __init__(self, config: FirebaseConfig | None = None) -> None:
        self._config = config or FirebaseConfig.from_env()
        if not self._config:
            raise ValueError(
                "No Firebase config available. Set ZENIC_FIREBASE_URL "
                "or pass a FirebaseConfig object."
            )

    # ── Request Listing ─────────────────────────────────────

    def list_pending_requests(self) -> list[ActivationRequest]:
        """Fetch all pending activation requests from Firebase."""
        import urllib.request

        url = f"{self._config.database_url}/activation_requests.json"
        if self._config.auth_secret:
            url += f"?auth={self._config.auth_secret}"

        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("Failed to fetch activation requests: %s", exc)
            return []

        if not data:
            return []

        requests: list[ActivationRequest] = []
        for req_id, req_data in data.items():
            if req_data.get("status", "pending") == "pending":
                requests.append(
                    ActivationRequest(
                        request_id=req_id,
                        activation_key=req_data.get("activation_key", ""),
                        device_id=req_data.get("device_id", ""),
                        username=req_data.get("username", "unknown"),
                        timestamp=req_data.get("timestamp", 0.0),
                        nonce=req_data.get("nonce", ""),
                        status="pending",
                    )
                )

        return sorted(requests, key=lambda r: r.timestamp)

    def get_request(self, request_id: str) -> ActivationRequest | None:
        """Fetch a specific activation request by ID."""
        import urllib.request

        url = f"{self._config.database_url}/activation_requests/{request_id}.json"
        if self._config.auth_secret:
            url += f"?auth={self._config.auth_secret}"

        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("Failed to fetch request %s: %s", request_id, exc)
            return None

        if not data:
            return None

        return ActivationRequest(
            request_id=request_id,
            activation_key=data.get("activation_key", ""),
            device_id=data.get("device_id", ""),
            username=data.get("username", "unknown"),
            timestamp=data.get("timestamp", 0.0),
            nonce=data.get("nonce", ""),
            status=data.get("status", "pending"),
        )

    # ── Request Processing ──────────────────────────────────

    def approve_request(
        self,
        request_id: str,
        license_data: dict[str, Any],
        notes: str = "",
    ) -> bool:
        """Approve a pending activation request and post the signed license.

        Args:
            request_id: The Firebase push ID of the request.
            license_data: The signed license data to return to the user.
            notes: Optional admin notes.

        Returns:
            True if the approval was posted successfully.
        """
        import urllib.request

        now = time.time()
        update_payload = {
            "status": "approved",
            "approved_at": now,
            "license": license_data,
            "notes": notes,
        }

        url = f"{self._config.database_url}/activation_requests/{request_id}.json"
        if self._config.auth_secret:
            url += f"?auth={self._config.auth_secret}"

        data_bytes = json.dumps(update_payload).encode()
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                logger.info(
                    "Request %s approved. License: %s",
                    request_id,
                    result.get("license", {}).get("license_id", "N/A"),
                )
                return True
        except Exception as exc:
            logger.error("Failed to approve request %s: %s", request_id, exc)
            return False

    def reject_request(self, request_id: str, reason: str = "") -> bool:
        """Reject a pending activation request."""
        import urllib.request

        update_payload = {
            "status": "rejected",
            "rejected_at": time.time(),
            "reason": reason or "Rejected by admin",
        }

        url = f"{self._config.database_url}/activation_requests/{request_id}.json"
        if self._config.auth_secret:
            url += f"?auth={self._config.auth_secret}"

        data_bytes = json.dumps(update_payload).encode()
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.info("Request %s rejected: %s", request_id, reason)
                return True
        except Exception as exc:
            logger.error("Failed to reject request %s: %s", request_id, exc)
            return False

    # ── CLI Display ─────────────────────────────────────────

    def display_requests(self, requests: list[ActivationRequest]) -> str:
        """Format a list of activation requests for CLI display."""
        if not requests:
            return "[yellow]No pending activation requests.[/]"

        lines = ["[bold]Pending Activation Requests[/]", ""]
        for i, req in enumerate(requests, 1):
            time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(req.timestamp)
            )
            lines.append(f"  #{i}: {req.request_id[:12]}...")
            lines.append(f"       User:      {req.username}")
            lines.append(f"       Key:       {req.activation_key[:20]}...")
            lines.append(f"       Device:    {req.device_id[:16]}...")
            lines.append(f"       Time:      {time_str}")
            lines.append("")

        return "\n".join(lines)


# ── CLI Entry Point ──────────────────────────────────────────


def main() -> None:
    """CLI entry point for managing activation requests."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="zenic-firebase-admin",
        description="Manage Zenic-Agents activation requests via Firebase",
    )
    parser.add_argument(
        "action",
        choices=["list", "inspect", "approve", "reject"],
        help="Action to perform",
    )
    parser.add_argument(
        "--request-id",
        "-r",
        help="Request ID (required for inspect/approve/reject)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for rejection",
    )
    parser.add_argument(
        "--notes",
        help="Admin notes for approval",
    )

    args = parser.parse_args()

    processor = ActivationRequestProcessor()

    if args.action == "list":
        requests = processor.list_pending_requests()
        print(processor.display_requests(requests))

    elif args.action == "inspect":
        if not args.request_id:
            print("Error: --request-id is required")
            return
        req = processor.get_request(args.request_id)
        if req:
            print(f"Request ID:    {req.request_id}")
            print(f"Username:      {req.username}")
            print(f"Activation Key: {req.activation_key}")
            print(f"Device ID:     {req.device_id}")
            print(f"Timestamp:     {time.ctime(req.timestamp)}")
            print(f"Status:        {req.status}")
        else:
            print(f"Request {args.request_id} not found.")

    elif args.action == "approve":
        if not args.request_id:
            print("Error: --request-id is required")
            return
        from ..license_mgmt.license_manager_cli import LicenseManagerCLI
        license_manager = LicenseManagerCLI()
        lic = license_manager.create_license(
            tier="starter",
            issued_to=args.request_id,
            notes=f"Auto-created for Firebase activation request {args.request_id}",
        )
        license_data = lic.__dict__
        success = processor.approve_request(
            args.request_id, license_data, notes=args.notes or ""
        )
        print(f"Request {'APPROVED' if success else 'FAILED'}")

    elif args.action == "reject":
        if not args.request_id:
            print("Error: --request-id is required")
            return
        success = processor.reject_request(
            args.request_id, reason=args.reason or ""
        )
        print(f"Request {'REJECTED' if success else 'FAILED'}")


if __name__ == "__main__":
    main()
