"""
Merkle Audit Trail — Immutable governance ledger for Zenic-Agents.

Provides cryptographic verification of all policy decisions,
audit entries, and governance actions. Every decision is hashed
into a Merkle tree, enabling:
- Tamper detection (any modification invalidates the chain)
- Compliance certificates (prove compliance without revealing data)
- Inclusion proofs (verify a specific entry exists in the trail)
"""

from ._engine import MerkleAuditEngine, get_merkle_audit_engine, reset_merkle_audit_engine
from ._types import (
    AuditEntryAction,
    ComplianceCertificate,
    MerkleAuditEntry,
    MerkleProofResult,
    MerkleVerificationResult,
)

__all__ = [
    "AuditEntryAction",
    "ComplianceCertificate",
    "MerkleAuditEngine",
    "MerkleAuditEntry",
    "MerkleProofResult",
    "MerkleVerificationResult",
    "get_merkle_audit_engine",
    "reset_merkle_audit_engine",
]
