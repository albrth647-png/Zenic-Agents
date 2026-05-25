//! High-Performance Shared Memory Bus — SharedMemoryBus.
//!
//! The canonical implementation lives in `src/bus/publisher.rs`.
//! This sub-module re-exports it for convenience.

mod types;
// methods.rs is intentionally empty — #[pymethods] is in publisher.rs

pub use types::SharedMemoryBus;
