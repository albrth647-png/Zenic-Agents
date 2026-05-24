//! Core PyO3 methods for SharedMemoryBus: pub/sub, broadcast, queries.
//!
//! NOTE: The canonical #[pymethods] implementation lives in `src/bus/publisher.rs`.
//! This file is intentionally empty — the methods were consolidated into
//! publisher.rs to eliminate the duplicate #[pymethods] impl block.
//!
//! PyO3 only allows one #[pymethods] per struct, so the implementation
//! must live in a single location. If you need to add methods, edit
//! `publisher.rs` directly.
