// ─── Niche Enums ────────────────────────────────────────────────────────
// NicheCategory, DataSensitivity, FieldRequirement, TemplateFieldType

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ═══════════════════════════════════════════════════════════════
//  NicheCategory — 7 cutting-edge industry categories
// ═══════════════════════════════════════════════════════════════

/// Industry category for a niche.
///
/// Each category groups related niches that share compliance
/// requirements, data sensitivity patterns, and workflow structures.
#[pyclass(name = "NicheCategory", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy, Serialize, Deserialize)]
pub enum NicheCategory {
    AiData,
    FinTech,
    HealthTech,
    GreenTech,
    EdTech,
    PropTech,
    LegalTech,
}

impl NicheCategory {
    /// Return the Python-enum string value.
    pub fn as_str(&self) -> &'static str {
        match self {
            NicheCategory::AiData => "ai_data",
            NicheCategory::FinTech => "fintech",
            NicheCategory::HealthTech => "healthtech",
            NicheCategory::GreenTech => "greentech",
            NicheCategory::EdTech => "edtech",
            NicheCategory::PropTech => "proptech",
            NicheCategory::LegalTech => "legaltech",
        }
    }

    /// Human-readable display name (Spanish).
    pub fn display_name(&self) -> &'static str {
        match self {
            NicheCategory::AiData => "IA y Datos",
            NicheCategory::FinTech => "Tecnología Financiera",
            NicheCategory::HealthTech => "Tecnología de la Salud",
            NicheCategory::GreenTech => "Tecnología Verde",
            NicheCategory::EdTech => "Tecnología Educativa",
            NicheCategory::PropTech => "Tecnología Inmobiliaria",
            NicheCategory::LegalTech => "Tecnología Jurídica",
        }
    }

    /// All variants in catalog order.
    pub fn all() -> &'static [NicheCategory] {
        &[
            NicheCategory::AiData,
            NicheCategory::FinTech,
            NicheCategory::HealthTech,
            NicheCategory::GreenTech,
            NicheCategory::EdTech,
            NicheCategory::PropTech,
            NicheCategory::LegalTech,
        ]
    }
}

#[pymethods]
impl NicheCategory {
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __repr__(&self) -> String {
        format!("NicheCategory.{}", self.display_name().replace(' ', ""))
    }

    /// Compliance standards for this category. Delegates to zenic-safety.
    fn compliance_standards(&self) -> Vec<String> {
        let canonical: zenic_safety::NicheCategory = (*self).into();
        canonical.compliance_standards()
            .iter().map(|s| s.to_string()).collect()
    }
}

// ═══════════════════════════════════════════════════════════════
//  DataSensitivity — 4 sensitivity levels
// ═══════════════════════════════════════════════════════════════

/// Data sensitivity classification for a niche.
#[pyclass(name = "DataSensitivity", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy, Serialize, Deserialize)]
pub enum DataSensitivity {
    Low,
    Medium,
    High,
    Critical,
}

impl DataSensitivity {
    pub fn as_str(&self) -> &'static str {
        match self {
            DataSensitivity::Low => "low",
            DataSensitivity::Medium => "medium",
            DataSensitivity::High => "high",
            DataSensitivity::Critical => "critical",
        }
    }

    /// Delegate level() to zenic-safety canonical implementation.
    pub fn level(&self) -> u8 {
        let canonical: zenic_safety::DataSensitivity = (*self).into();
        canonical.level()
    }

    /// Delegate requires_escalation() to zenic-safety.
    pub fn requires_escalation(&self) -> bool {
        let canonical: zenic_safety::DataSensitivity = (*self).into();
        canonical.requires_escalation()
    }

    /// Delegate escalate_verdict() to zenic-safety.
    pub fn escalate_verdict(&self) -> crate::safety_gate::types::SafetyVerdict {
        let canonical: zenic_safety::DataSensitivity = (*self).into();
        canonical.escalate_verdict().into()
    }
}

impl Default for DataSensitivity {
    fn default() -> Self {
        DataSensitivity::Low
    }
}

impl Ord for DataSensitivity {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        let a: zenic_safety::DataSensitivity = (*self).into();
        let b: zenic_safety::DataSensitivity = (*other).into();
        a.cmp(&b)
    }
}

impl PartialOrd for DataSensitivity {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[pymethods]
impl DataSensitivity {
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __repr__(&self) -> String {
        format!("DataSensitivity.{}", self.as_str().to_uppercase())
    }

    /// Numeric level (0=Low .. 3=Critical). Delegates to zenic-safety.
    #[getter]
    fn level(&self) -> u8 {
        DataSensitivity::level(self)
    }

    /// Whether escalation is required. Delegates to zenic-safety.
    fn requires_escalation(&self) -> bool {
        DataSensitivity::requires_escalation(self)
    }
}

// ═══════════════════════════════════════════════════════════════
//  FieldRequirement — field requirement classification
// ═══════════════════════════════════════════════════════════════

/// Whether a template field is required, optional, or conditional.
#[pyclass(name = "FieldRequirement", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy, Serialize, Deserialize)]
pub enum FieldRequirement {
    Required,
    Optional,
    Conditional,
}

impl FieldRequirement {
    pub fn as_str(&self) -> &'static str {
        match self {
            FieldRequirement::Required => "required",
            FieldRequirement::Optional => "optional",
            FieldRequirement::Conditional => "conditional",
        }
    }
}

#[pymethods]
impl FieldRequirement {
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __repr__(&self) -> String {
        format!("FieldRequirement.{}", self.as_str().to_uppercase())
    }
}

// ═══════════════════════════════════════════════════════════════
//  TemplateFieldType — 14 field types for template schemas
// ═══════════════════════════════════════════════════════════════

/// Type of a template field, controlling validation and UI rendering.
#[pyclass(name = "TemplateFieldType", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy, Serialize, Deserialize)]
pub enum TemplateFieldType {
    Text,
    Number,
    Boolean,
    Date,
    DateTime,
    Email,
    Url,
    Phone,
    Currency,
    Percentage,
    Json,
    Enum,
    Reference,
    File,
}

impl TemplateFieldType {
    pub fn as_str(&self) -> &'static str {
        match self {
            TemplateFieldType::Text => "text",
            TemplateFieldType::Number => "number",
            TemplateFieldType::Boolean => "boolean",
            TemplateFieldType::Date => "date",
            TemplateFieldType::DateTime => "datetime",
            TemplateFieldType::Email => "email",
            TemplateFieldType::Url => "url",
            TemplateFieldType::Phone => "phone",
            TemplateFieldType::Currency => "currency",
            TemplateFieldType::Percentage => "percentage",
            TemplateFieldType::Json => "json",
            TemplateFieldType::Enum => "enum",
            TemplateFieldType::Reference => "reference",
            TemplateFieldType::File => "file",
        }
    }
}

#[pymethods]
impl TemplateFieldType {
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __repr__(&self) -> String {
        format!("TemplateFieldType.{}", self.as_str().to_uppercase())
    }
}

// ═══════════════════════════════════════════════════════════════
//  Interop with zenic-safety — From conversions
//
//  These impls allow seamless conversion between the PyO3-exposed
//  types in this module and the canonical zenic-safety types. This
//  eliminates the duplication while keeping the PyO3 #[pyclass]
//  attributes required for Python interop.
// ═══════════════════════════════════════════════════════════════

impl From<zenic_safety::NicheCategory> for NicheCategory {
    fn from(c: zenic_safety::NicheCategory) -> Self {
        match c {
            zenic_safety::NicheCategory::AiData => NicheCategory::AiData,
            zenic_safety::NicheCategory::FinTech => NicheCategory::FinTech,
            zenic_safety::NicheCategory::HealthTech => NicheCategory::HealthTech,
            zenic_safety::NicheCategory::GreenTech => NicheCategory::GreenTech,
            zenic_safety::NicheCategory::EdTech => NicheCategory::EdTech,
            zenic_safety::NicheCategory::PropTech => NicheCategory::PropTech,
            zenic_safety::NicheCategory::LegalTech => NicheCategory::LegalTech,
        }
    }
}

impl From<NicheCategory> for zenic_safety::NicheCategory {
    fn from(c: NicheCategory) -> Self {
        match c {
            NicheCategory::AiData => zenic_safety::NicheCategory::AiData,
            NicheCategory::FinTech => zenic_safety::NicheCategory::FinTech,
            NicheCategory::HealthTech => zenic_safety::NicheCategory::HealthTech,
            NicheCategory::GreenTech => zenic_safety::NicheCategory::GreenTech,
            NicheCategory::EdTech => zenic_safety::NicheCategory::EdTech,
            NicheCategory::PropTech => zenic_safety::NicheCategory::PropTech,
            NicheCategory::LegalTech => zenic_safety::NicheCategory::LegalTech,
        }
    }
}

impl From<zenic_safety::DataSensitivity> for DataSensitivity {
    fn from(s: zenic_safety::DataSensitivity) -> Self {
        match s {
            zenic_safety::DataSensitivity::Low => DataSensitivity::Low,
            zenic_safety::DataSensitivity::Medium => DataSensitivity::Medium,
            zenic_safety::DataSensitivity::High => DataSensitivity::High,
            zenic_safety::DataSensitivity::Critical => DataSensitivity::Critical,
        }
    }
}

impl From<DataSensitivity> for zenic_safety::DataSensitivity {
    fn from(s: DataSensitivity) -> Self {
        match s {
            DataSensitivity::Low => zenic_safety::DataSensitivity::Low,
            DataSensitivity::Medium => zenic_safety::DataSensitivity::Medium,
            DataSensitivity::High => zenic_safety::DataSensitivity::High,
            DataSensitivity::Critical => zenic_safety::DataSensitivity::Critical,
        }
    }
}
