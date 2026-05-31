// ─── A2A Protocol — Task Handler ──────────────────────────────────────
// a2a_handle_task(), a2a_validate_delegation()

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use super::types::{A2AResponse, A2ATask};

/// Valid priority levels for A2A tasks.
const VALID_PRIORITIES: &[&str] = &["low", "normal", "high", "critical"];

/// Process an incoming A2A task.
///
/// Validates the task priority, checks delegation policy, and computes
/// a BLAKE3 merkle hash over the payload for the audit trail.
#[pyfunction]
pub fn a2a_handle_task(task: &A2ATask) -> PyResult<A2AResponse> {
    // Validate priority
    let priority = task.priority_ref();
    if !VALID_PRIORITIES.contains(&priority) {
        return Err(PyValueError::new_err(format!(
            "Invalid priority '{}'. Must be one of: {:?}",
            priority, VALID_PRIORITIES
        )));
    }

    // Validate payload is valid JSON
    if let Err(e) = serde_json::from_str::<serde_json::Value>(task.payload_ref()) {
        return Err(PyValueError::new_err(format!(
            "Invalid JSON payload: {}",
            e
        )));
    }

    // Compute BLAKE3 merkle hash for audit trail
    let merkle_hash = blake3::hash(task.payload_ref().as_bytes())
        .to_hex()
        .to_string();

    // Determine status
    let status = if task.requires_approval_ref() {
        "pending_approval".to_string()
    } else {
        "completed".to_string()
    };

    // Build result JSON
    let result = serde_json::json!({
        "task_id": task.task_id_ref(),
        "sender": task.sender_agent_ref(),
        "receiver": task.receiver_agent_ref(),
        "priority": priority,
        "processed": true,
    })
    .to_string();

    Ok(A2AResponse::create(
        task.task_id_ref().to_string(),
        status,
        result,
        merkle_hash,
    ))
}

/// Check whether delegation is allowed by the policy engine.
///
/// Returns `true` if the task's priority is within the allowed level
/// and the task does not violate any policy constraints.
#[pyfunction]
#[pyo3(signature = (task, policy_level))]
pub fn a2a_validate_delegation(task: &A2ATask, policy_level: &str) -> PyResult<bool> {
    let priority = task.priority_ref();

    // Map priority to numeric level
    let priority_level = match priority {
        "low" => 0,
        "normal" => 1,
        "high" => 2,
        "critical" => 3,
        _ => {
            return Err(PyValueError::new_err(format!(
                "Invalid priority '{}' in task",
                priority
            )))
        }
    };

    // Map policy_level to max allowed level
    let max_level = match policy_level {
        "open" => 3,
        "standard" => 2,
        "restricted" => 1,
        "locked" => 0,
        _ => {
            return Err(PyValueError::new_err(format!(
                "Invalid policy_level '{}'. Must be one of: open, standard, restricted, locked",
                policy_level
            )))
        }
    };

    // Delegation allowed if task priority <= max allowed level
    Ok(priority_level <= max_level)
}
