// ─── Niche Schema Types ──────────────────────────────────────────────────
// TemplateFieldSchema, TemplateSection

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::api::log_niche_error;
use super::enums::{FieldRequirement, TemplateFieldType};

// ═══════════════════════════════════════════════════════════════
//  TemplateFieldSchema — single field definition
// ═══════════════════════════════════════════════════════════════

/// Schema definition for a single field within a template section.
///
/// Each field has:
/// - Identity: name (machine), display_name (human)
/// - Type: TemplateFieldType controlling validation
/// - Requirement: required / optional / conditional
/// - Default: optional default value as string
/// - Validation: key-value validation rules (min, max, pattern, etc.)
/// - Order: display ordering within section
///
/// All fields are read-only from Python via getters.
#[pyclass(name = "TemplateFieldSchema")]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TemplateFieldSchema {
    name: String,
    display_name: String,
    field_type: TemplateFieldType,
    requirement: FieldRequirement,
    default_value: Option<String>,
    description: String,
    condition: String,
    validation: HashMap<String, String>,
    enum_variants: Vec<String>,
    reference_entity: String,
    file_accept: Vec<String>,
    order: usize,
}

impl TemplateFieldSchema {
    /// Create a new TemplateFieldSchema with validation.
    pub fn new(
        name: String,
        display_name: String,
        field_type: TemplateFieldType,
        requirement: FieldRequirement,
    ) -> Self {
        let name_trimmed = name.trim().to_string();
        if name_trimmed.is_empty() {
            log_niche_error("TemplateFieldSchema: name cannot be empty");
        }
        TemplateFieldSchema {
            name: name_trimmed,
            display_name,
            field_type,
            requirement,
            default_value: None,
            description: String::new(),
            condition: String::new(),
            validation: HashMap::new(),
            enum_variants: Vec::new(),
            reference_entity: String::new(),
            file_accept: Vec::new(),
            order: 0,
        }
    }

    /// Get the field name (machine-readable identifier).
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Get the display name.
    pub fn display_name(&self) -> &str {
        &self.display_name
    }

    /// Get the field type.
    pub fn field_type(&self) -> TemplateFieldType {
        self.field_type
    }

    /// Get the requirement.
    pub fn requirement(&self) -> FieldRequirement {
        self.requirement
    }

    /// Check if this field is required.
    pub fn is_required(&self) -> bool {
        self.requirement == FieldRequirement::Required
    }

    /// Get the default value.
    pub fn default_value(&self) -> Option<&str> {
        self.default_value.as_deref()
    }

    /// Get the description.
    pub fn description(&self) -> &str {
        &self.description
    }

    /// Get the condition.
    pub fn condition(&self) -> &str {
        &self.condition
    }

    /// Get the enum variants.
    pub fn enum_variants(&self) -> Vec<String> {
        self.enum_variants.clone()
    }

    /// Get the reference entity.
    pub fn reference_entity(&self) -> &str {
        &self.reference_entity
    }

    /// Get the file accept types.
    pub fn file_accept(&self) -> Vec<String> {
        self.file_accept.clone()
    }

    /// Get the display order.
    pub fn order(&self) -> usize {
        self.order
    }
}

#[pymethods]
impl TemplateFieldSchema {
    #[getter(name)]
    fn py_get_name(&self) -> &str {
        &self.name
    }

    #[getter(display_name)]
    fn py_get_display_name(&self) -> &str {
        &self.display_name
    }

    #[getter(field_type)]
    fn py_get_field_type(&self) -> TemplateFieldType {
        self.field_type
    }

    #[getter(requirement)]
    fn py_get_requirement(&self) -> FieldRequirement {
        self.requirement
    }

    #[getter(default_value)]
    fn py_get_default_value(&self) -> Option<&str> {
        self.default_value.as_deref()
    }

    #[getter(description)]
    fn py_get_description(&self) -> &str {
        &self.description
    }

    #[getter(condition)]
    fn py_get_condition(&self) -> &str {
        &self.condition
    }

    #[getter]
    fn validation(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new_bound(py);
        for (k, v) in &self.validation {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter(enum_variants)]
    fn py_get_enum_variants(&self) -> Vec<String> {
        self.enum_variants.clone()
    }

    #[getter(reference_entity)]
    fn py_get_reference_entity(&self) -> &str {
        &self.reference_entity
    }

    #[getter(file_accept)]
    fn py_get_file_accept(&self) -> Vec<String> {
        self.file_accept.clone()
    }

    #[getter(order)]
    fn py_get_order(&self) -> usize {
        self.order
    }

    /// Check if this field is required.
    fn py_is_required(&self) -> bool {
        self.requirement == FieldRequirement::Required
    }

    /// Check if this field is conditional.
    fn py_is_conditional(&self) -> bool {
        self.requirement == FieldRequirement::Conditional
    }

    fn __repr__(&self) -> String {
        format!(
            "TemplateFieldSchema(name={:?}, type={}, requirement={})",
            self.name,
            self.field_type.as_str(),
            self.requirement.as_str(),
        )
    }
}

// ═══════════════════════════════════════════════════════════════
//  TemplateSection — group of related fields
// ═══════════════════════════════════════════════════════════════

/// A section within a niche template, grouping related fields.
#[pyclass(name = "TemplateSection")]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TemplateSection {
    section_id: String,
    title: String,
    description: String,
    fields: Vec<TemplateFieldSchema>,
    order: usize,
}

impl TemplateSection {
    /// Create a new TemplateSection with the given identity.
    pub fn new(section_id: String, title: String) -> Self {
        TemplateSection {
            section_id,
            title,
            description: String::new(),
            fields: Vec::new(),
            order: 0,
        }
    }

    /// Add a field to this section.
    pub fn add_field(&mut self, field: TemplateFieldSchema) {
        self.fields.push(field);
    }

    /// Set the description (used by catalog builders).
    pub(crate) fn set_description(&mut self, value: String) {
        self.description = value;
    }

    /// Set the display order (used by catalog builders).
    pub(crate) fn set_order(&mut self, value: usize) {
        self.order = value;
    }

    /// Get the section_id.
    pub fn section_id(&self) -> &str {
        &self.section_id
    }

    /// Get the title.
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Get the description.
    pub fn description(&self) -> &str {
        &self.description
    }

    /// Get the display order.
    pub fn order(&self) -> usize {
        self.order
    }

    /// Get all fields.
    pub fn fields(&self) -> &[TemplateFieldSchema] {
        &self.fields
    }

    /// Count required fields.
    pub fn required_field_count(&self) -> usize {
        self.fields.iter().filter(|f| f.is_required()).count()
    }
}

#[pymethods]
impl TemplateSection {
    #[getter(section_id)]
    fn py_get_section_id(&self) -> &str {
        &self.section_id
    }

    #[getter(title)]
    fn py_get_title(&self) -> &str {
        &self.title
    }

    #[getter(description)]
    fn py_get_description(&self) -> &str {
        &self.description
    }

    #[getter(order)]
    fn py_get_order(&self) -> usize {
        self.order
    }

    /// Get the number of fields in this section.
    fn field_count(&self) -> usize {
        self.fields.len()
    }

    /// Get the number of required fields in this section.
    fn required_count(&self) -> usize {
        self.required_field_count()
    }

    /// Get a list of all field names in this section.
    fn field_names(&self) -> Vec<String> {
        self.fields.iter().map(|f| f.name.clone()).collect()
    }

    /// Get a field by name. Returns None if not found.
    fn get_field(&self, name: &str) -> Option<TemplateFieldSchema> {
        self.fields.iter().find(|f| f.name == name).cloned()
    }

    fn __repr__(&self) -> String {
        format!(
            "TemplateSection(id={:?}, title={:?}, fields={})",
            self.section_id,
            self.title,
            self.fields.len(),
        )
    }
}
