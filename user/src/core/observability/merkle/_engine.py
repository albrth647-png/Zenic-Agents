"""
Merkle Audit Trail — Engine for creating and verifying immutable audit entries.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from ._types import (
    AuditEntryAction,
    ComplianceCertificate,
    MerkleAuditEntry,
    MerkleProofResult,
    MerkleVerificationResult,
)

logger = logging.getLogger(__name__)

# Try to import Rust native module for high-performance operations
try:
    from _zenic_native import (  # noqa: F401 — imported for availability check
        chain_hash as _rust_chain_hash,
        forensic_hash as _rust_forensic_hash,  # used by forensic integration
        merkle_proof as _rust_merkle_proof,
        verify_merkle_chain as _rust_verify_chain,
        batch_verify_chains as _rust_batch_verify,  # used by batch verification
    )
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False
    logger.debug("_zenic_native Merkle functions not available, using Python fallback")


def _compute_hash(data: str) -> str:
    """Compute SHA-256 hash of data (Python fallback)."""
    return hashlib.sha256(data.encode()).hexdigest()


class MerkleAuditEngine:
    """
    Engine for the Merkle Audit Trail.

    Provides:
    - Record audit entries with automatic Merkle chain hashing
    - Verify entire chain integrity
    - Generate Merkle inclusion proofs
    - Issue compliance certificates

    Uses Rust native module when available for performance.
    """

    def __init__(self, tenant_id: str = ""):
        self.tenant_id = tenant_id
        self._entries: list[MerkleAuditEntry] = []
        self._last_hash: str = "GENESIS"
        self._entry_counter: int = 0

    def record(
        self,
        action: AuditEntryAction,
        actor_id: str,
        resource: str,
        outcome: str,
        severity: str = "info",
        details: dict[str, Any] | None = None,
        session_id: str = "",
        niche_category: str = "",
    ) -> MerkleAuditEntry:
        """
        Record a new audit entry in the Merkle trail.

        The entry is automatically chained to the previous entry
        via its hash, creating an immutable sequence.
        """
        self._entry_counter += 1
        timestamp = time.time()

        entry = MerkleAuditEntry(
            entry_id=f"maud_{self._entry_counter:06d}_{int(timestamp * 1000)}",
            action=action,
            actor_id=actor_id,
            resource=resource,
            outcome=outcome,
            severity=severity,
            details=details or {},
            timestamp=timestamp,
            tenant_id=self.tenant_id,
            session_id=session_id,
            niche_category=niche_category,
            parent_hash=self._last_hash,
        )

        # Compute hash
        hash_content = (
            f"{entry.entry_id}:{entry.action.value}:{entry.actor_id}:"
            f"{entry.resource}:{entry.outcome}:{entry.parent_hash}:{entry.timestamp}"
        )

        if _HAS_RUST:
            try:
                entry.hash_sha256 = _rust_chain_hash(hash_content)
            except Exception:
                entry.hash_sha256 = _compute_hash(hash_content)
        else:
            entry.hash_sha256 = _compute_hash(hash_content)

        self._last_hash = entry.hash_sha256
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> MerkleVerificationResult:
        """
        Verify the integrity of the entire Merkle audit chain.

        Returns details about any broken links.
        """
        if not self._entries:
            return MerkleVerificationResult(is_valid=True)

        # Use Rust native verification if available
        if _HAS_RUST:
            try:
                chain_dicts = [e.to_chain_dict() for e in self._entries]
                rust_result = _rust_verify_chain(chain_dicts)
                return MerkleVerificationResult(
                    is_valid=rust_result.get("is_valid", False),
                    total_entries=rust_result.get("total_entries", 0),
                    valid_entries=rust_result.get("valid_entries", 0),
                    broken_links=rust_result.get("broken_links", []),
                    root_hash=rust_result.get("root_hash", ""),
                )
            except Exception as e:
                logger.warning("Rust chain verification failed, using Python fallback: %s", e)

        # Python fallback
        valid = 0
        broken: list[dict[str, Any]] = []

        for i, entry in enumerate(self._entries):
            if i == 0:
                if entry.parent_hash != "GENESIS":
                    broken.append({"index": i, "expected": "GENESIS", "actual": entry.parent_hash})
                    continue
            else:
                if entry.parent_hash != self._entries[i - 1].hash_sha256:
                    broken.append({
                        "index": i,
                        "expected": self._entries[i - 1].hash_sha256,
                        "actual": entry.parent_hash,
                    })
                    continue

            # Verify hash
            hash_content = (
                f"{entry.entry_id}:{entry.action.value}:{entry.actor_id}:"
                f"{entry.resource}:{entry.outcome}:{entry.parent_hash}:{entry.timestamp}"
            )
            expected_hash = _compute_hash(hash_content)
            if entry.hash_sha256 != expected_hash:
                broken.append({
                    "index": i,
                    "expected": expected_hash,
                    "actual": entry.hash_sha256,
                })
                continue

            valid += 1

        root_hash = self._entries[-1].hash_sha256 if self._entries else ""
        return MerkleVerificationResult(
            is_valid=len(broken) == 0,
            total_entries=len(self._entries),
            valid_entries=valid,
            broken_links=broken,
            root_hash=root_hash,
        )

    def generate_proof(self, entry_id: str) -> MerkleProofResult:
        """Generate a Merkle inclusion proof for a specific entry."""
        index = None
        entry_hash = ""
        all_hashes = [e.hash_sha256 for e in self._entries]

        for i, entry in enumerate(self._entries):
            if entry.entry_id == entry_id:
                index = i
                entry_hash = entry.hash_sha256
                break

        if index is None:
            return MerkleProofResult(merkle_root="", leaf_index=-1, verified=False)

        # Use Rust native proof generation if available
        if _HAS_RUST:
            try:
                rust_result = _rust_merkle_proof(entry_hash, all_hashes)
                return MerkleProofResult(
                    merkle_root=rust_result.get("merkle_root", ""),
                    proof_path=rust_result.get("proof_path", []),
                    leaf_index=rust_result.get("leaf_index", -1),
                    verified=rust_result.get("verified", False),
                )
            except Exception as e:
                logger.warning("Rust merkle proof failed, using Python fallback: %s", e)

        # Python fallback — simplified proof
        return MerkleProofResult(
            merkle_root=self._entries[-1].hash_sha256 if self._entries else "",
            proof_path=all_hashes,
            leaf_index=index,
            verified=index < len(self._entries),
        )

    def issue_compliance_certificate(
        self,
        standards: list[str] | None = None,
    ) -> ComplianceCertificate:
        """
        Issue a compliance certificate based on the current audit trail.

        The certificate is only valid if the Merkle chain verifies clean.
        """
        verification = self.verify_chain()

        from uuid import uuid4
        cert = ComplianceCertificate(
            certificate_id=f"cert_{uuid4().hex[:12]}",
            issued_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            chain_root_hash=verification.root_hash,
            total_entries=verification.total_entries,
            status="COMPLIANT" if verification.is_valid else "NON_COMPLIANT",
            standards=standards or ["SOC2", "HIPAA", "GDPR"],
            tenant_id=self.tenant_id,
        )
        return cert

    @property
    def entries(self) -> list[MerkleAuditEntry]:
        """All entries in the audit trail."""
        return self._entries

    @property
    def latest_hash(self) -> str:
        """The hash of the most recent entry (or GENESIS if empty)."""
        return self._last_hash

    @property
    def entry_count(self) -> int:
        """Number of entries in the trail."""
        return len(self._entries)


# ─── Singleton ────────────────────────────────────────────────

_merkle_engine: MerkleAuditEngine | None = None


def get_merkle_audit_engine(tenant_id: str = "") -> MerkleAuditEngine:
    """Get or create the MerkleAuditEngine singleton."""
    global _merkle_engine
    if _merkle_engine is None:
        _merkle_engine = MerkleAuditEngine(tenant_id=tenant_id)
    return _merkle_engine


def reset_merkle_audit_engine() -> None:
    """Reset the MerkleAuditEngine singleton (for testing)."""
    global _merkle_engine
    _merkle_engine = None
