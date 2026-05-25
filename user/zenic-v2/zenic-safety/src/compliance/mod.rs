//! Compliance validation engine — regulatory standards checker.
//!
//! Supports 10 compliance standards:
//!   HIPAA, PCI-DSS, GDPR, SOX, AML/KYC, FedRAMP, COPPA, ISO 27001, SOC 2, PCI-DSS 1.2
//!
//! Sub-modules:
//! - [`types`] — ComplianceStandard and ComplianceResult types
//! - [`engine_impl`] — ComplianceEngine with all standard check implementations + enforce()
//! - [`checker`] — Compatibility re-export (delegates to engine_impl)
//! - [`reporter`] — Report formatting and integration tests

pub mod checker;
pub mod engine_impl;
pub mod reporter;
pub mod types;

// Convenience re-exports — preserves the original public API surface.
pub use engine_impl::ComplianceEngine;
pub use reporter::format_compliance_report;
pub use types::{ComplianceBlockError, ComplianceResult, ComplianceStandard};
