//! Store operations for the Memory Chip.
//!
//! Contains helper functions for mapping CRUD, HITL approval,
//! Merkle sealing, and YAML rendering — extracted from the
//! MemoryChip PyO3 methods.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

use zenic_memory::{HitlOutcome, SemanticMapping};

use super::types::{mem_err_to_py, parse_mechanism, MemoryChipInner};

/// Inserts a new semantic mapping into the graph.
///
/// Returns the mapping_id of the newly created mapping.
pub(crate) fn insert_mapping(
    inner: &MemoryChipInner,
    origin: &str,
    relation: &str,
    destination: &str,
    mechanism: &str,
    tenant_id: &str,
) -> PyResult<String> {
    let mech = parse_mechanism(mechanism)?;

    // Check feature gate
    {
        let gate = inner.gate.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Gate lock poisoned: {}", e))
        })?;
        gate.check_mechanism(mech).map_err(mem_err_to_py)?;
    }

    // Check mapping quota
    let count = {
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph.count_mappings(tenant_id).map_err(mem_err_to_py)?
    };
    {
        let gate = inner.gate.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Gate lock poisoned: {}", e))
        })?;
        gate.check_mapping_quota(count).map_err(mem_err_to_py)?;
    }

    let mapping_id = uuid::Uuid::new_v4().to_string();
    let mapping = SemanticMapping::new(
        mapping_id.clone(),
        origin.to_string(),
        relation.to_string(),
        destination.to_string(),
        mech,
    );
    let mut mapping_with_tenant = mapping;
    mapping_with_tenant.tenant_id = tenant_id.to_string();

    {
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph
            .insert_mapping(&mapping_with_tenant)
            .map_err(mem_err_to_py)?;

        // Audit log — failure is logged but non-blocking
        if let Err(e) = graph.audit_log(
            &mapping_id,
            "insert",
            "memory_chip",
            &format!("{}:{}:{}", origin, relation, destination),
        ) {
            tracing::warn!("Audit log failed for insert mapping '{}': {}", mapping_id, e);
        }
    }

    // Insert into cache (non-critical, log on failure)
    if let Err(e) = inner.cache.insert(origin, &mapping_with_tenant, tenant_id) {
        tracing::debug!("Cache insert failed for mapping '{}': {}", mapping_id, e);
    }

    Ok(mapping_id)
}

/// Approves a mapping with HITL mandatory fields.
///
/// Validates the 3 mandatory HITL fields:
/// 1. admin_evidence_review must be true
/// 2. admin_justification must be >= 50 characters
/// 3. risk_acknowledgment must be true + admin_session_id non-empty
///
/// Returns true if approval succeeded.
pub(crate) fn approve_mapping(
    inner: &MemoryChipInner,
    mapping_id: &str,
    admin_evidence_review: bool,
    admin_justification: &str,
    risk_acknowledgment: bool,
    admin_session_id: &str,
) -> PyResult<bool> {
    // Approve through HITL bridge
    let outcome = {
        let mut bridge = inner.hitl_bridge.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("HITL bridge lock poisoned: {}", e))
        })?;
        bridge
            .approve(
                mapping_id,
                admin_evidence_review,
                admin_justification.to_string(),
                risk_acknowledgment,
                admin_session_id.to_string(),
            )
            .map_err(mem_err_to_py)?
    };

    if outcome == HitlOutcome::Approved {
        // Compute a real merkle-derived hash for approval instead of a placeholder
        let approval_hash = {
            let mut seal = inner.merkle_seal.lock().map_err(|e| {
                PyRuntimeError::new_err(format!("Merkle seal lock poisoned: {}", e))
            })?;
            // Use the HITL approval data to generate a deterministic hash
            let approval_data = format!(
                "{}:{}:{}:{}",
                mapping_id,
                admin_evidence_review,
                admin_justification.len(),
                risk_acknowledgment
            );
            seal.seal_approval(&approval_data).map_err(mem_err_to_py)?
        };
        {
            let graph = inner.graph.lock().map_err(|e| {
                PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
            })?;
            graph
                .approve_mapping(mapping_id, &approval_hash)
                .map_err(mem_err_to_py)?;

            // Audit log — failure is logged but non-blocking
            if let Err(e) = graph.audit_log(
                mapping_id,
                "approve",
                admin_session_id,
                &format!(
                    "evidence_review={}, justification_len={}",
                    admin_evidence_review,
                    admin_justification.len()
                ),
            ) {
                tracing::warn!("Audit log failed for approve mapping '{}': {}", mapping_id, e);
            }
        }
    }

    Ok(outcome == HitlOutcome::Approved)
}

/// Seals a mapping with a Merkle hash.
///
/// Fetches the REAL mapping data from the SemanticGraph by mapping_id,
/// then computes and stores the Merkle hash. This ensures the integrity
/// seal reflects the actual data, not synthetic placeholders.
///
/// Returns the merkle_hash hex string.
pub(crate) fn seal_mapping(inner: &MemoryChipInner, mapping_id: &str) -> PyResult<String> {
    // FIX: Fetch the REAL mapping from the graph instead of using synthetic data.
    let mapping = {
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph
            .get_mapping_by_id(mapping_id)
            .map_err(mem_err_to_py)?
            .ok_or_else(|| {
                PyRuntimeError::new_err(format!(
                    "Cannot seal mapping '{}': not found in graph",
                    mapping_id
                ))
            })?
    };

    // Seal with Merkle using the REAL mapping data
    let merkle_hash = {
        let mut seal = inner.merkle_seal.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Merkle seal lock poisoned: {}", e))
        })?;
        seal.seal_mapping(&mapping).map_err(mem_err_to_py)?
    };

    // Update the graph with the real merkle hash
    {
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph
            .approve_mapping(mapping_id, &merkle_hash)
            .map_err(mem_err_to_py)?;
    }

    Ok(merkle_hash)
}

/// Renders a mapping as YAML for policy hot-reload.
///
/// Fetches the REAL mapping from the SemanticGraph by mapping_id.
/// If no approved HITL request is found, uses the mapping's own data
/// to construct a render-safe approval request.
///
/// Returns the YAML string.
pub(crate) fn render_yaml(inner: &MemoryChipInner, mapping_id: &str) -> PyResult<String> {
    // FIX: Fetch the REAL mapping from the graph instead of using synthetic data.
    let mapping = {
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph
            .get_mapping_by_id(mapping_id)
            .map_err(mem_err_to_py)?
            .ok_or_else(|| {
                PyRuntimeError::new_err(format!(
                    "Cannot render mapping '{}': not found in graph",
                    mapping_id
                ))
            })?
    };

    // Try to find the completed HITL approval for this mapping
    let approval = {
        let bridge = inner.hitl_bridge.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("HITL bridge lock poisoned: {}", e))
        })?;
        bridge
            .find_completed(mapping_id)
            .cloned()
            .unwrap_or_else(|| {
                // Fallback: construct a render-safe approval from the mapping
                zenic_memory::MemoryApprovalRequest {
                    admin_evidence_review: true,
                    admin_justification: format!(
                        "Rendered via MemoryChip.render_yaml() — mapping '{}' not yet approved",
                        mapping_id
                    ),
                    risk_acknowledgment: false,
                    admin_session_id: String::new(),
                    mapping_id: mapping_id.to_string(),
                    ia_question: mapping.binary_question(),
                    ia_response: false,
                    evidence_for: vec![],
                    evidence_against: vec!["unapproved_mapping".to_string()],
                    consensus_score: 0.0,
                }
            })
    };

    let renderer = inner.yaml_renderer.lock().map_err(|e| {
        PyRuntimeError::new_err(format!("YAML renderer lock poisoned: {}", e))
    })?;
    renderer
        .render_mapping(&mapping, &approval)
        .map_err(mem_err_to_py)
}

/// Counts the number of mappings for a tenant.
pub(crate) fn count_mappings(inner: &MemoryChipInner, tenant_id: &str) -> PyResult<u32> {
    let graph = inner.graph.lock().map_err(|e| {
        PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
    })?;
    graph.count_mappings(tenant_id).map_err(mem_err_to_py)
}
