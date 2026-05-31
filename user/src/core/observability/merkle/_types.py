"""
Merkle Audit Trail — Type definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuditEntryAction(Enum):
    """Types of actions that can be recorded in the Merkle audit trail."""
    POLICY_ALLOW = "policy_allow"
    POLICY_DENY = "policy_deny"
    HITL_APPROVE = "hitl_approve"
    HITL_REJECT = "hitl_reject"
    A2A_DELEGATE = "a2a_delegate"
    A2A_RECEIVE = "a2a_receive"
    NICHE_DNA_GENERATE = "niche_dna_generate"
    BLUEPRINT_CERTIFY = "blueprint_certify"
    SAFETY_VETO = "safety_veto"
    ROLLBACK_EXECUTE = "rollback_execute"
    CONFIG_CHANGE = "config_change"
    DATA_ACCESS = "data_access"


@dataclass
class MerkleAuditEntry:
    """A single entry in the Merkle audit trail."""
    entry_id: str
    action: AuditEntryAction
    actor_id: str
    resource: str
    outcome: str  # success, failure, denied, error
    severity: str = "info"  # debug, info, warn, error, critical
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    tenant_id: str = ""
    session_id: str = ""
    niche_category: str = ""
    # Merkle fields (populated by engine)
    hash_sha256: str = ""
    parent_hash: str = ""

    def to_chain_dict(self) -> dict[str, Any]:
        """Convert to dict format for Rust native verify_merkle_chain."""
        return {
            "id": self.entry_id,
            "hash_sha256": self.hash_sha256,
            "parent_hash": self.parent_hash,
            "file_path": self.resource,
            "operation": self.action.value,
            "timestamp": self.timestamp,
        }


@dataclass
class MerkleVerificationResult:
    """Result of verifying the Merkle audit chain."""
    is_valid: bool
    total_entries: int = 0
    valid_entries: int = 0
    broken_links: list[dict[str, Any]] = field(default_factory=list)
    root_hash: str = ""


@dataclass
class MerkleProofResult:
    """Result of generating a Merkle inclusion proof."""
    merkle_root: str
    proof_path: list[str] = field(default_factory=list)
    leaf_index: int = -1
    verified: bool = False


@dataclass
class ComplianceCertificate:
    """A compliance certificate generated from the Merkle audit trail."""
    certificate_id: str
    issued_at: str
    chain_root_hash: str
    total_entries: int
    status: str  # COMPLIANT, NON_COMPLIANT
    standards: list[str] = field(default_factory=list)
    valid_from: str = ""
    valid_until: str = ""
    tenant_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "issued_at": self.issued_at,
            "chain_root_hash": self.chain_root_hash,
            "total_entries": self.total_entries,
            "status": self.status,
            "standards": self.standards,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "tenant_id": self.tenant_id,
        }
