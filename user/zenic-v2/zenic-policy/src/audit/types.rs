//! Audit types: PolicyDecision, DenialReason, PolicyAuditEntry, AuditLog.

use serde::{Deserialize, Serialize};
use std::fmt;
use zenic_proto::{SessionId, TenantId};

use crate::permission::Permission;
use crate::role::RoleId;

// ---------------------------------------------------------------------------
// PolicyDecision
// ---------------------------------------------------------------------------

/// Outcome of a policy evaluation.
///
/// Each evaluation produces one of these decisions, which is then
/// recorded in the audit log.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PolicyDecision {
    /// The action is allowed by the policy engine.
    Allowed,
    /// The action is denied by the policy engine.
    Denied,
}

impl fmt::Display for PolicyDecision {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Allowed => write!(f, "allowed"),
            Self::Denied => write!(f, "denied"),
        }
    }
}

// ---------------------------------------------------------------------------
// DenialReason
// ---------------------------------------------------------------------------

/// Why a policy evaluation resulted in a denial.
///
/// Denials can occur for several reasons, each with different
/// implications for the caller. This enum captures the specific
/// reason so that the audit log provides actionable information.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DenialReason {
    /// No role assigned to the session grants the required permission.
    NoMatchingRole,
    /// A policy rule explicitly denied the action.
    RuleDenied(String),
    /// A safety veto blocked the action.
    SafetyVeto(String),
    /// The session's roles lack the criticality clearance.
    CriticalityGate,
    /// No policy rule matched (default-deny).
    DefaultDeny,
}

impl fmt::Display for DenialReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoMatchingRole => write!(f, "no_matching_role"),
            Self::RuleDenied(name) => write!(f, "rule_denied:{}", name),
            Self::SafetyVeto(name) => write!(f, "safety_veto:{}", name),
            Self::CriticalityGate => write!(f, "criticality_gate"),
            Self::DefaultDeny => write!(f, "default_deny"),
        }
    }
}

// ---------------------------------------------------------------------------
// PolicyAuditEntry
// ---------------------------------------------------------------------------

/// A single audit entry recording a policy decision.
///
/// Audit entries are immutable once created. They capture the full
/// context of a policy evaluation, including the session, tenant,
/// requested permission, and the outcome.
///
/// Each entry includes a BLAKE3 Merkle hash that chains it to the
/// previous entry, creating a tamper-evident audit trail.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicyAuditEntry {
    /// Monotonic timestamp when this decision was made (milliseconds).
    pub timestamp_ms: u64,
    /// The session that requested the action.
    pub session_id: SessionId,
    /// The tenant within which the action was requested.
    pub tenant_id: TenantId,
    /// The permission that was evaluated.
    pub permission: Permission,
    /// The decision outcome.
    pub decision: PolicyDecision,
    /// Why the decision was made (only set for denials).
    pub denial_reason: Option<DenialReason>,
    /// The roles that were considered during evaluation.
    pub role_ids: Vec<RoleId>,
    /// BLAKE3 merkle hash of this entry (for immutable audit trail).
    /// Computed from all other fields + previous entry's hash.
    pub merkle_hash: String,
    /// Hash of the previous audit entry (chain link).
    pub previous_hash: String,
}

impl PolicyAuditEntry {
    /// Creates a new audit entry for an allowed decision.
    pub fn allowed(
        timestamp_ms: u64,
        session_id: SessionId,
        tenant_id: TenantId,
        permission: Permission,
        role_ids: Vec<RoleId>,
        previous_hash: &str,
    ) -> Self {
        let mut entry = Self {
            timestamp_ms,
            session_id,
            tenant_id,
            permission,
            decision: PolicyDecision::Allowed,
            denial_reason: None,
            role_ids,
            merkle_hash: String::new(), // placeholder — computed below
            previous_hash: previous_hash.to_string(),
        };
        entry.merkle_hash = entry.compute_entry_hash();
        entry
    }

    /// Creates a new audit entry for a denied decision.
    pub fn denied(
        timestamp_ms: u64,
        session_id: SessionId,
        tenant_id: TenantId,
        permission: Permission,
        reason: DenialReason,
        role_ids: Vec<RoleId>,
        previous_hash: &str,
    ) -> Self {
        let mut entry = Self {
            timestamp_ms,
            session_id,
            tenant_id,
            permission,
            decision: PolicyDecision::Denied,
            denial_reason: Some(reason),
            role_ids,
            merkle_hash: String::new(), // placeholder — computed below
            previous_hash: previous_hash.to_string(),
        };
        entry.merkle_hash = entry.compute_entry_hash();
        entry
    }

    /// Whether this entry records a denial.
    pub fn is_denial(&self) -> bool {
        self.decision == PolicyDecision::Denied
    }

    /// Whether this entry records an allowance.
    pub fn is_allowance(&self) -> bool {
        self.decision == PolicyDecision::Allowed
    }

    /// Compute the BLAKE3 hash of this entry's content (excluding merkle_hash itself).
    fn compute_entry_hash(&self) -> String {
        let content = format!(
            "{}:{}:{}:{}:{}:{}:{}",
            self.timestamp_ms,
            self.session_id,
            self.tenant_id,
            serde_json::to_string(&self.permission).unwrap_or_default(),
            self.decision,
            serde_json::to_string(&self.denial_reason).unwrap_or_default(),
            self.previous_hash,
        );
        blake3::hash(content.as_bytes()).to_hex().to_string()
    }
}

// ---------------------------------------------------------------------------
// AuditLog
// ---------------------------------------------------------------------------

/// In-memory audit log for policy decisions with Merkle chain integrity.
///
/// The audit log records every policy evaluation. Each entry is chained
/// to the previous one via BLAKE3 hashes, creating a tamper-evident
/// audit trail. For Phase 4, the log is stored in memory. The
/// `zenic-core` crate will add disk persistence later.
pub struct AuditLog {
    entries: Vec<PolicyAuditEntry>,
    /// Monotonic clock for timestamps (milliseconds).
    clock_ms: u64,
    /// Hash of the last entry added (chain tip). Starts as "GENESIS".
    last_hash: String,
}

impl AuditLog {
    /// Creates an empty audit log.
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
            clock_ms: 0,
            last_hash: "GENESIS".to_string(),
        }
    }

    /// Records an allowed decision in the audit log.
    pub fn record_allowed(
        &mut self,
        session_id: SessionId,
        tenant_id: TenantId,
        permission: Permission,
        role_ids: Vec<RoleId>,
    ) {
        let entry = PolicyAuditEntry::allowed(
            self.next_timestamp(),
            session_id,
            tenant_id,
            permission,
            role_ids,
            self.last_hash.as_str(),
        );
        self.last_hash = entry.merkle_hash.clone();
        self.entries.push(entry);
    }

    /// Records a denied decision in the audit log.
    pub fn record_denied(
        &mut self,
        session_id: SessionId,
        tenant_id: TenantId,
        permission: Permission,
        reason: DenialReason,
        role_ids: Vec<RoleId>,
    ) {
        let entry = PolicyAuditEntry::denied(
            self.next_timestamp(),
            session_id,
            tenant_id,
            permission,
            reason,
            role_ids,
            self.last_hash.as_str(),
        );
        self.last_hash = entry.merkle_hash.clone();
        self.entries.push(entry);
    }

    /// Returns the number of entries in the audit log.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Whether the audit log is empty.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns all entries in chronological order.
    pub fn entries(&self) -> &[PolicyAuditEntry] {
        &self.entries
    }

    /// Returns all denial entries.
    pub fn denials(&self) -> Vec<&PolicyAuditEntry> {
        self.entries.iter().filter(|e| e.is_denial()).collect()
    }

    /// Returns all allowance entries.
    pub fn allowances(&self) -> Vec<&PolicyAuditEntry> {
        self.entries.iter().filter(|e| e.is_allowance()).collect()
    }

    /// Returns entries for a specific session.
    pub fn entries_for_session(&self, session_id: &SessionId) -> Vec<&PolicyAuditEntry> {
        self.entries
            .iter()
            .filter(|e| &e.session_id == session_id)
            .collect()
    }

    /// Returns entries for a specific tenant.
    pub fn entries_for_tenant(&self, tenant_id: &TenantId) -> Vec<&PolicyAuditEntry> {
        self.entries
            .iter()
            .filter(|e| &e.tenant_id == tenant_id)
            .collect()
    }

    /// Verify the entire audit chain integrity.
    /// Returns Ok(()) if all entries form a valid Merkle chain,
    /// or Err with the index of the first broken link.
    pub fn verify_chain(&self) -> Result<(), usize> {
        for (i, entry) in self.entries.iter().enumerate() {
            // Verify hash
            let expected_hash = entry.compute_entry_hash();
            if entry.merkle_hash != expected_hash {
                return Err(i);
            }
            // Verify chain link
            if i == 0 {
                if entry.previous_hash != "GENESIS" {
                    return Err(0);
                }
            } else {
                if entry.previous_hash != self.entries[i - 1].merkle_hash {
                    return Err(i);
                }
            }
        }
        Ok(())
    }

    /// Generate a Merkle inclusion proof for a specific entry.
    /// Returns the proof path (sibling hashes) needed to verify inclusion.
    pub fn merkle_proof(&self, index: usize) -> Option<Vec<String>> {
        if index >= self.entries.len() {
            return None;
        }
        // Simple proof: collect all sibling hashes from leaf to root
        let hashes: Vec<String> = self.entries.iter().map(|e| e.merkle_hash.clone()).collect();
        let mut proof = Vec::new();
        let mut idx = index;

        // Build tree levels
        let mut current: Vec<String> = hashes;
        while current.len() > 1 {
            if current.len() % 2 != 0 {
                current.push(current.last().unwrap().clone());
            }
            if idx % 2 == 0 && idx + 1 < current.len() {
                proof.push(current[idx + 1].clone());
            } else if idx > 0 {
                proof.push(current[idx - 1].clone());
            }
            current = current.chunks(2).map(|chunk| {
                let combined = format!("{}{}", chunk[0], chunk[1]);
                blake3::hash(combined.as_bytes()).to_hex().to_string()
            }).collect();
            idx /= 2;
        }
        Some(proof)
    }

    /// Get the root hash of the Merkle tree.
    pub fn root_hash(&self) -> String {
        if self.entries.is_empty() {
            return "EMPTY".to_string();
        }
        let hashes: Vec<String> = self.entries.iter().map(|e| e.merkle_hash.clone()).collect();
        if hashes.len() == 1 {
            return hashes[0].clone();
        }
        let mut current = hashes;
        while current.len() > 1 {
            if current.len() % 2 != 0 {
                current.push(current.last().unwrap().clone());
            }
            current = current.chunks(2).map(|chunk| {
                let combined = format!("{}{}", chunk[0], chunk[1]);
                blake3::hash(combined.as_bytes()).to_hex().to_string()
            }).collect();
        }
        current[0].clone()
    }

    /// Returns the next monotonic timestamp and advances the clock.
    fn next_timestamp(&mut self) -> u64 {
        let ts = self.clock_ms;
        self.clock_ms += 1;
        ts
    }
}

impl Default for AuditLog {
    fn default() -> Self {
        Self::new()
    }
}
