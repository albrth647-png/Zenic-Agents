//! A2A (Agent-to-Agent) Protocol — Google A2A interoperability for Zenic-Agents.
//!
//! This module implements the core types and operations for the A2A protocol,
//! enabling agents to discover each other, delegate tasks, and maintain
//! audit trails across agent boundaries.
//!
//! # Sub-modules
//!
//! - `types`: Core data types (AgentCard, A2ATask, A2AResponse) with PyO3 bindings
//! - `handler`: Task processing and delegation validation
//! - `discovery`: Agent registration and capability-based discovery

pub mod discovery;
pub mod handler;
pub mod types;

// Re-export key types for convenient access via `crate::a2a::AgentCard` etc.
pub use discovery::{
    a2a_discover_agents, a2a_get_agent_card, a2a_list_registered_agents, a2a_register_agent,
};
pub use handler::{a2a_handle_task, a2a_validate_delegation};
pub use types::{A2AResponse, A2ATask, AgentCard};
