//! Lifecycle phase transitions — DELEGATED to `orchestrator.rs` and `orchestrator_run.rs`.
//!
//! The `impl LifecycleOrchestrator` blocks that were previously here (construction,
//! episode execution, and accessor methods) are now consolidated in:
//! - `orchestrator.rs` — struct definition, `new()`, `new_for_tier()`, and accessor methods
//! - `orchestrator_run.rs` — `run_episode()`, `complete_episode_after_hitl()`,
//!   `complete_episode_internal()`
//!
//! This file is kept as a module placeholder for backward compatibility.
