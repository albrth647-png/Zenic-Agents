// ─── A2A Protocol — Agent Discovery ───────────────────────────────────
// a2a_register_agent(), a2a_discover_agents(), a2a_get_agent_card(),
// a2a_list_registered_agents()

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Mutex;

use super::types::AgentCard;

/// In-memory registry of A2A agents, keyed by agent ID.
static AGENT_REGISTRY: Lazy<Mutex<HashMap<String, AgentCard>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

/// Register an agent in the local A2A registry.
///
/// Returns `true` if the agent was newly registered, `false` if an
/// agent with the same ID already existed (the existing entry is
/// overwritten with the new card).
#[pyfunction]
pub fn a2a_register_agent(card: &AgentCard) -> PyResult<bool> {
    let mut registry = AGENT_REGISTRY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Registry lock poisoned: {}", e))
    })?;
    let is_new = !registry.contains_key(card.id_ref());
    registry.insert(card.id_ref().to_string(), card.clone());
    Ok(is_new)
}

/// Discover agents by capability and optionally by niche.
///
/// Returns all agents whose capability list includes the requested
/// capability. If `niche` is provided, further filters to agents
/// whose `niche_dna` matches.
#[pyfunction]
#[pyo3(signature = (capability, niche=None))]
pub fn a2a_discover_agents(capability: &str, niche: Option<&str>) -> PyResult<Vec<AgentCard>> {
    let registry = AGENT_REGISTRY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Registry lock poisoned: {}", e))
    })?;

    let results: Vec<AgentCard> = registry
        .values()
        .filter(|card| {
            // Must have the requested capability
            let has_cap = card.capabilities_ref().iter().any(|c| c == capability);
            if !has_cap {
                return false;
            }
            // If niche filter specified, must match niche_dna
            if let Some(n) = niche {
                match card.niche_dna_ref() {
                    Some(dna) => dna == n,
                    None => false,
                }
            } else {
                true
            }
        })
        .cloned()
        .collect();

    Ok(results)
}

/// Get an agent card by ID.
///
/// Returns `None` if no agent with the given ID is registered.
#[pyfunction]
pub fn a2a_get_agent_card(agent_id: &str) -> PyResult<Option<AgentCard>> {
    let registry = AGENT_REGISTRY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Registry lock poisoned: {}", e))
    })?;
    Ok(registry.get(agent_id).cloned())
}

/// List all registered agents.
#[pyfunction]
pub fn a2a_list_registered_agents() -> PyResult<Vec<AgentCard>> {
    let registry = AGENT_REGISTRY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Registry lock poisoned: {}", e))
    })?;
    Ok(registry.values().cloned().collect())
}
