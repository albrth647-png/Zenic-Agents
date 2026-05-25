//! # zenic-subscription
//!
//! Subscription engine with Saga pattern, USDT TRC20 payments,
//! and 14-day trial for Zenic-Agents v3.0.0.
//!
//! This crate provides:
//! - [`SubscriptionTier`] — 5-tier model (Starter, Business, Enterprise, On-Premise Enterprise, Setup Fee)
//! - [`Subscription`] — Full subscription state machine
//! - [`Trial`] — 14-day automatic trial (Business plan for ALL users)
//! - [`UsdtPayment`] — USDT TRC20 payment model (manual/semi-manual)
//! - [`SubscriptionFeatureGate`] — Feature gates per tier
//! - [`UsageMeter`] — Usage metering and limits enforcement
//! - [`saga`] — Saga pattern for subscription lifecycle reliability
//! - [`SubscriptionEngine`] — Main orchestrator

pub mod engine;
pub mod errors;
pub mod feature_gates;
pub mod payment;
pub mod pricing;
pub mod saga;
pub mod trial;
pub mod types;
pub mod usage;

// Convenience re-exports.
pub use engine::SubscriptionEngine;
pub use errors::SubscriptionError;
pub use feature_gates::SubscriptionFeatureGate;
pub use payment::{PaymentStatus, PaymentVerification, UsdtPayment, UsdtPaymentMethod};
pub use pricing::PricingEngine;
pub use saga::{
    CancellationSaga, PaymentSaga, RenewalSaga, SagaContext, SagaStepResult, SignupSaga,
    SubscriptionSaga, UpgradeSaga,
};
pub use trial::{Trial, TrialManager, TrialStatus};
pub use types::{
    AddOn, AddOnId, Subscription, SubscriptionStatus, SubscriptionTier, SubscriptionTierName,
    TierLimits,
};
pub use usage::{UsageMeter, UsageRecord, UsageType};
