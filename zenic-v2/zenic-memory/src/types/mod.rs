//! Type definitions for the Adaptive Binary Memory Chip.
//!
//! Split into two modules:
//! - [`core`] — Fundamental value types: LearningMechanism, SemanticMapping, NodeValue
//! - [`lifecycle`] — Lifecycle types: LearningVerdict, MemoryApprovalRequest, Hypothesis, MemoryTierLimits

pub mod core;
pub mod lifecycle;

// Convenience re-exports — preserves the original public API surface
// so that `use crate::types::X` continues to work unchanged.
pub use core::{LearningMechanism, NodeValue, SemanticMapping};
pub use lifecycle::{
    MemoryTierLimits, Hypothesis, LearningVerdict, MemoryApprovalRequest, SubscriptionTier,
};
