//! SharedMemoryBus struct definition and field types.
//!
//! The canonical definition lives in `src/bus/publisher.rs`.
//! This module re-exports it to maintain backward compatibility
//! if the `shared_memory_bus` sub-module is activated.

pub use crate::bus::publisher::SharedMemoryBus;
