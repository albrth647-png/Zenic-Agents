//! Memory Chip — PyO3 operations (construction, lookup, adaptation, CRUD).

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use zenic_memory::{
    HitlOutcome, LearningMechanism, SemanticMapping,
};

use super::types::{
    MemoryChip, MemoryChipBuilder, mem_err_to_py, parse_mechanism, parse_tier, mapping_to_pydict,
};

#[pymethods]
impl MemoryChip {
    /// Creates a new MemoryChip with a SQLite database path.
    #[new]
    fn new(db_path: &str) -> PyResult<Self> {
        let builder = MemoryChipBuilder::new(db_path.to_string());
        let inner = builder.build().map_err(mem_err_to_py)?;
        Ok(Self {
            inner: std::sync::Arc::new(std::sync::Mutex::new(inner)),
        })
    }

    /// Creates a MemoryChip with a specific subscription tier.
    #[pyo3(signature = (db_path, tier))]
    #[staticmethod]
    fn with_tier(db_path: &str, tier: &str) -> PyResult<Self> {
        let subscription_tier = parse_tier(tier)?;
        let builder = MemoryChipBuilder::new(db_path.to_string()).tier(subscription_tier);
        let inner = builder.build().map_err(mem_err_to_py)?;
        Ok(Self {
            inner: std::sync::Arc::new(std::sync::Mutex::new(inner)),
        })
    }

    // ─── Lookup & Adaptation ────────────────────────────────────

    /// Looks up a term in the memory chip.
    fn lookup(&self, py: Python<'_>, text: &str, tenant_id: &str) -> PyResult<Py<PyDict>> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

        // 1. Check LRU cache first (<1μs)
        if let Some(mapping) = inner.cache.lookup(text, tenant_id) {
            return Ok(mapping_to_pydict(py, &mapping, true)?);
        }

        // 2. Check ontology base
        if let Some(mapping) = inner.ontology.lookup(text, tenant_id) {
            if let Err(_e) = inner.cache.insert(text, &mapping, tenant_id) {
                // Cache warm-up is non-critical; ignore errors silently
            }
            return Ok(mapping_to_pydict(py, &mapping, false)?);
        }

        // 3. Check SQLite (<2ms)
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        match graph.lookup(text, tenant_id) {
            Ok(Some(mapping)) => {
                if let Err(_e) = inner.cache.insert(text, &mapping, tenant_id) {
                    // Cache warm-up is non-critical; ignore errors silently
                }
                Ok(mapping_to_pydict(py, &mapping, false)?)
            }
            Ok(None) => {
                let result = PyDict::new_bound(py);
                result.set_item("cache_hit", false)?;
                result.set_item("mapping", py.None())?;
                result.set_item("origin", text)?;
                result.set_item("destination", "")?;
                Ok(result.unbind())
            }
            Err(e) => Err(mem_err_to_py(e)),
        }
    }

    /// Tries to adapt a failed DAG field using learned mappings.
    fn try_adapt(&self, py: Python<'_>, failed_field: &str, tenant_id: &str) -> PyResult<Py<PyDict>> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

        // 1. Check cache first
        if let Some(mapping) = inner.cache.lookup(failed_field, tenant_id) {
            if mapping.approved {
                let result = PyDict::new_bound(py);
                result.set_item("adapted", true)?;
                result.set_item("corrected_field", &mapping.destination)?;
                result.set_item("mapping_id", &mapping.mapping_id)?;
                return Ok(result.unbind());
            }
        }

        // 2. Check ontology
        if let Some(mapping) = inner.ontology.lookup(failed_field, tenant_id) {
            if mapping.approved {
                if let Err(e) = inner.cache.insert(failed_field, &mapping, tenant_id) {
                    tracing::debug!("Cache insert failed in try_adapt: {}", e);
                }
                let result = PyDict::new_bound(py);
                result.set_item("adapted", true)?;
                result.set_item("corrected_field", &mapping.destination)?;
                result.set_item("mapping_id", &mapping.mapping_id)?;
                return Ok(result.unbind());
            }
        }

        // 3. Check SQLite
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        match graph.lookup(failed_field, tenant_id) {
            Ok(Some(mapping)) => {
                if mapping.approved {
                    if let Err(e) = inner.cache.insert(failed_field, &mapping, tenant_id) {
                        tracing::debug!("Cache insert failed in try_adapt: {}", e);
                    }
                    let result = PyDict::new_bound(py);
                    result.set_item("adapted", true)?;
                    result.set_item("corrected_field", &mapping.destination)?;
                    result.set_item("mapping_id", &mapping.mapping_id)?;
                    Ok(result.unbind())
                } else {
                    let result = PyDict::new_bound(py);
                    result.set_item("adapted", false)?;
                    result.set_item("corrected_field", py.None())?;
                    result.set_item("mapping_id", py.None())?;
                    Ok(result.unbind())
                }
            }
            Ok(None) => {
                let result = PyDict::new_bound(py);
                result.set_item("adapted", false)?;
                result.set_item("corrected_field", py.None())?;
                result.set_item("mapping_id", py.None())?;
                Ok(result.unbind())
            }
            Err(e) => Err(mem_err_to_py(e)),
        }
    }

    // ─── Mapping CRUD ────────────────────────────────────────────

    /// Inserts a new semantic mapping into the graph.
    #[pyo3(signature = (origin, relation, destination, mechanism, tenant_id))]
    fn insert_mapping(
        &self,
        origin: &str,
        relation: &str,
        destination: &str,
        mechanism: &str,
        tenant_id: &str,
    ) -> PyResult<String> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

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
    #[pyo3(signature = (mapping_id, admin_evidence_review, admin_justification, risk_acknowledgment, admin_session_id))]
    fn approve_mapping(
        &self,
        mapping_id: &str,
        admin_evidence_review: bool,
        admin_justification: &str,
        risk_acknowledgment: bool,
        admin_session_id: &str,
    ) -> PyResult<bool> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

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
            // Compute a real merkle hash for approval instead of a placeholder
            let approval_hash = {
                let seal = inner.merkle_seal.lock().map_err(|e| {
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
    /// FIX: Fetches the REAL mapping from the SemanticGraph instead of
    /// using synthetic placeholder data. This ensures the Merkle integrity
    /// seal reflects the actual mapping content.
    fn seal_mapping(&self, mapping_id: &str) -> PyResult<String> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

        // FIX: Fetch the REAL mapping from the graph instead of synthetic data
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

        let merkle_hash = {
            let mut seal = inner.merkle_seal.lock().map_err(|e| {
                PyRuntimeError::new_err(format!("Merkle seal lock poisoned: {}", e))
            })?;
            seal.seal_mapping(&mapping).map_err(mem_err_to_py)?
        };

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
    /// FIX: Fetches the REAL mapping from the SemanticGraph and looks up
    /// the completed HITL approval. Falls back to a render-safe request
    /// if no approval is found, marking the mapping as unapproved.
    fn render_yaml(&self, mapping_id: &str) -> PyResult<String> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;

        // FIX: Fetch the REAL mapping from the graph instead of synthetic data
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
                    // Fallback: construct a render-safe approval marking as unapproved
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
    fn count_mappings(&self, tenant_id: &str) -> PyResult<u32> {
        let inner = self.inner.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Lock poisoned: {}", e))
        })?;
        let graph = inner.graph.lock().map_err(|e| {
            PyRuntimeError::new_err(format!("Graph lock poisoned: {}", e))
        })?;
        graph.count_mappings(tenant_id).map_err(mem_err_to_py)
    }
}
