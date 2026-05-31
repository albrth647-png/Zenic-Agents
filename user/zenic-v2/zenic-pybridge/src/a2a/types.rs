// ─── A2A Protocol — Types ─────────────────────────────────────────────
// AgentCard, A2ATask, A2AResponse — PyO3-exposed types for the
// Google A2A (Agent-to-Agent) interoperability protocol.

use pyo3::prelude::*;

// ═══════════════════════════════════════════════════════════════
//  AgentCard — Agent identity and capability descriptor
// ═══════════════════════════════════════════════════════════════

/// Agent card describing an A2A agent's identity, capabilities, and policy.
#[pyclass(name = "AgentCard")]
#[derive(Clone, Debug)]
pub struct AgentCard {
    /// Unique agent identifier.
    id: String,
    /// Human-readable agent name.
    name: String,
    /// Agent description.
    description: String,
    /// Optional niche DNA fingerprint.
    niche_dna: Option<String>,
    /// List of capability identifiers this agent supports.
    capabilities: Vec<String>,
    /// Endpoint URL for reaching this agent.
    endpoint: String,
    /// Whether this agent requires human-in-the-loop approval.
    requires_hitl: bool,
    /// Policy constraints governing this agent's behaviour.
    policy_constraints: Vec<String>,
}

#[pymethods]
impl AgentCard {
    #[new]
    #[pyo3(signature = (id, name, description, niche_dna=None, capabilities=Vec::new(), endpoint=String::new(), requires_hitl=false, policy_constraints=Vec::new()))]
    fn new(
        id: String,
        name: String,
        description: String,
        niche_dna: Option<String>,
        capabilities: Vec<String>,
        endpoint: String,
        requires_hitl: bool,
        policy_constraints: Vec<String>,
    ) -> Self {
        AgentCard {
            id,
            name,
            description,
            niche_dna,
            capabilities,
            endpoint,
            requires_hitl,
            policy_constraints,
        }
    }

    #[getter]
    fn id(&self) -> &str {
        &self.id
    }

    #[getter]
    fn name(&self) -> &str {
        &self.name
    }

    #[getter]
    fn description(&self) -> &str {
        &self.description
    }

    #[getter]
    fn niche_dna(&self) -> Option<&str> {
        self.niche_dna.as_deref()
    }

    #[getter]
    fn capabilities(&self) -> Vec<String> {
        self.capabilities.clone()
    }

    #[getter]
    fn endpoint(&self) -> &str {
        &self.endpoint
    }

    #[getter]
    fn requires_hitl(&self) -> bool {
        self.requires_hitl
    }

    #[getter]
    fn policy_constraints(&self) -> Vec<String> {
        self.policy_constraints.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "AgentCard(id='{}', name='{}', capabilities={:?})",
            self.id, self.name, self.capabilities
        )
    }
}

// Public field accessors for internal Rust usage.
impl AgentCard {
    pub fn id_ref(&self) -> &str {
        &self.id
    }

    pub fn capabilities_ref(&self) -> &[String] {
        &self.capabilities
    }

    pub fn niche_dna_ref(&self) -> Option<&str> {
        self.niche_dna.as_deref()
    }
}

// ═══════════════════════════════════════════════════════════════
//  A2ATask — Inter-agent task descriptor
// ═══════════════════════════════════════════════════════════════

/// A task sent from one agent to another via the A2A protocol.
#[pyclass(name = "A2ATask")]
#[derive(Clone, Debug)]
pub struct A2ATask {
    /// Unique task identifier.
    task_id: String,
    /// ID of the agent sending the task.
    sender_agent: String,
    /// ID of the agent receiving the task.
    receiver_agent: String,
    /// JSON-encoded payload for the task.
    payload: String,
    /// Priority level: "low", "normal", "high", or "critical".
    priority: String,
    /// Whether this task requires explicit approval before execution.
    requires_approval: bool,
    /// Optional niche category classification.
    niche_category: Option<String>,
}

#[pymethods]
impl A2ATask {
    #[new]
    #[pyo3(signature = (task_id, sender_agent, receiver_agent, payload, priority="normal".to_string(), requires_approval=false, niche_category=None))]
    fn new(
        task_id: String,
        sender_agent: String,
        receiver_agent: String,
        payload: String,
        priority: String,
        requires_approval: bool,
        niche_category: Option<String>,
    ) -> Self {
        A2ATask {
            task_id,
            sender_agent,
            receiver_agent,
            payload,
            priority,
            requires_approval,
            niche_category,
        }
    }

    #[getter]
    fn task_id(&self) -> &str {
        &self.task_id
    }

    #[getter]
    fn sender_agent(&self) -> &str {
        &self.sender_agent
    }

    #[getter]
    fn receiver_agent(&self) -> &str {
        &self.receiver_agent
    }

    #[getter]
    fn payload(&self) -> &str {
        &self.payload
    }

    #[getter]
    fn priority(&self) -> &str {
        &self.priority
    }

    #[getter]
    fn requires_approval(&self) -> bool {
        self.requires_approval
    }

    #[getter]
    fn niche_category(&self) -> Option<&str> {
        self.niche_category.as_deref()
    }

    fn __repr__(&self) -> String {
        format!(
            "A2ATask(task_id='{}', sender='{}', receiver='{}', priority='{}')",
            self.task_id, self.sender_agent, self.receiver_agent, self.priority
        )
    }
}

// Public field accessors for internal Rust usage.
impl A2ATask {
    pub fn task_id_ref(&self) -> &str {
        &self.task_id
    }

    pub fn sender_agent_ref(&self) -> &str {
        &self.sender_agent
    }

    pub fn receiver_agent_ref(&self) -> &str {
        &self.receiver_agent
    }

    pub fn payload_ref(&self) -> &str {
        &self.payload
    }

    pub fn priority_ref(&self) -> &str {
        &self.priority
    }

    pub fn requires_approval_ref(&self) -> bool {
        self.requires_approval
    }
}

// ═══════════════════════════════════════════════════════════════
//  A2AResponse — Response to an A2A task with audit trail
// ═══════════════════════════════════════════════════════════════

/// Response from an A2A task, including an integrity hash for the audit trail.
#[pyclass(name = "A2AResponse")]
#[derive(Clone, Debug)]
pub struct A2AResponse {
    /// ID of the task this response belongs to.
    task_id: String,
    /// Status of the task (e.g. "completed", "rejected", "pending_approval").
    status: String,
    /// JSON-encoded result payload.
    result: String,
    /// BLAKE3 merkle hash for audit trail integrity.
    merkle_hash: String,
}

#[pymethods]
impl A2AResponse {
    #[new]
    #[pyo3(signature = (task_id, status, result, merkle_hash))]
    fn new(
        task_id: String,
        status: String,
        result: String,
        merkle_hash: String,
    ) -> Self {
        A2AResponse {
            task_id,
            status,
            result,
            merkle_hash,
        }
    }

    #[getter]
    fn task_id(&self) -> &str {
        &self.task_id
    }

    #[getter]
    fn status(&self) -> &str {
        &self.status
    }

    #[getter]
    fn result(&self) -> &str {
        &self.result
    }

    #[getter]
    fn merkle_hash(&self) -> &str {
        &self.merkle_hash
    }

    fn __repr__(&self) -> String {
        format!(
            "A2AResponse(task_id='{}', status='{}', merkle_hash='{}')",
            self.task_id, self.status, self.merkle_hash
        )
    }
}

// Public constructor for internal Rust usage.
impl A2AResponse {
    pub fn create(
        task_id: String,
        status: String,
        result: String,
        merkle_hash: String,
    ) -> Self {
        A2AResponse {
            task_id,
            status,
            result,
            merkle_hash,
        }
    }
}
