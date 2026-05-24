//! Learning Lifecycle — Saga workflow for learning episodes [T1+T2]
//!
//! Manages the full lifecycle of a memory learning episode from
//! hypothesis to validated knowledge. Uses Saga pattern for reliability.
//!
//! Flow:
//! 1. Deterministic Layer proposes hypothesis
//! 2. IA classifies SÍ/NO (Layer 4 only if needed)
//! 3. HITL validates with 3 mandatory fields
//! 4. MerkleLedger seals with BLAKE3
//! 5. YAML rendered for hot-reload
//! 6. Cache LRU updated
//! 7. Next time: Layer 1 resolves in <5ms, IA not activated
//!
//! Phase 4 enhancements:
//! - LifecycleOrchestrator: full integration of all Memory Chip components
//! - CompensationAction: Saga compensation tracking
//! - Episode persistence: write/load to learning_audit table
//! - Automatic phase transitions with component calls

// ---------------------------------------------------------------------------
// Submodules
// ---------------------------------------------------------------------------

pub mod manager;
pub mod orchestrator;
pub mod orchestrator_run;
pub mod persistence;
pub mod transitions;
pub mod types;

// ---------------------------------------------------------------------------
// Re-exports — every public symbol accessible from `crate::lifecycle::*`
// ---------------------------------------------------------------------------

pub use orchestrator::LifecycleOrchestrator;

pub use types::{
    CompensationAction, EpisodeOutcome, EpisodeResult, LifecycleEpisode, LifecyclePhase,
};

pub use manager::LifecycleManager;
