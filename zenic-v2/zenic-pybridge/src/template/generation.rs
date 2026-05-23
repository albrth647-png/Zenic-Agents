//! Template generation functions.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::catalog::catalog_get_by_id;
use crate::niche::{
    FieldRequirement, NicheDefinition, TemplateFieldType,
};

/// Generate a YAML template skeleton from a niche_id.
///
/// This is the core function of the dynamic template system.
/// It takes a niche_id, looks up the NicheDefinition in the
/// compiled catalog, and generates a Python dict representing
/// the YAML template with all fields set to null.
///
/// Parameters
/// ----------
/// niche_id : str
///     The niche identifier from the catalog.
///
/// Returns
/// -------
/// dict or None
///     The template dict if niche found, None otherwise.
#[pyfunction]
pub fn template_generate(niche_id: &str, py: Python<'_>) -> PyResult<Option<Py<PyDict>>> {
    let niche = match catalog_get_by_id(niche_id) {
        Some(n) => n,
        None => return Ok(None),
    };
    generate_template_dict(&niche, py).map(Some)
}

/// Generate a template from an existing NicheDefinition.
#[pyfunction]
pub fn template_generate_from_niche(niche: &NicheDefinition, py: Python<'_>) -> PyResult<Py<PyDict>> {
    generate_template_dict(niche, py)
}

/// Internal: build the template dict from a NicheDefinition.
pub(crate) fn generate_template_dict(niche: &NicheDefinition, py: Python<'_>) -> PyResult<Py<PyDict>> {
    let root = PyDict::new_bound(py);
    let template = PyDict::new_bound(py);

    // ── Metadata ────────────────────────────────────────────
    let metadata = PyDict::new_bound(py);
    metadata.set_item("niche_id", niche.niche_id()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set niche_id: {}", e)))?;
    metadata.set_item("niche_name", niche.name()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set niche_name: {}", e)))?;
    metadata.set_item("version", niche.version()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set version: {}", e)))?;
    metadata.set_item("domain", niche.domain()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set domain: {}", e)))?;
    metadata.set_item("subdomain", niche.subdomain()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set subdomain: {}", e)))?;
    metadata.set_item("category", niche.category().as_str()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set category: {}", e)))?;
    metadata.set_item("data_sensitivity", niche.data_sensitivity().as_str()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set data_sensitivity: {}", e)))?;
    metadata.set_item("scale", niche.scale()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set scale: {}", e)))?;
    metadata.set_item("compliance", niche.compliance()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set compliance: {}", e)))?;
    metadata.set_item("required_documents", niche.required_documents()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set required_documents: {}", e)))?;
    metadata.set_item("tags", niche.tags()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set tags: {}", e)))?;
    metadata.set_item("status", "incomplete").map_err(|e| PyRuntimeError::new_err(format!("Failed to set status: {}", e)))?;

    let now = chrono::Utc::now().to_rfc3339();
    metadata.set_item("generated_at", now.as_str()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set generated_at: {}", e)))?;

    template.set_item("metadata", metadata).map_err(|e| PyRuntimeError::new_err(format!("Failed to set metadata: {}", e)))?;

    // ── Sections ────────────────────────────────────────────
    let sections = PyDict::new_bound(py);
    let mut total_fields: usize = 0;

    for section in niche.template_sections() {
        let section_dict = PyDict::new_bound(py);
        section_dict.set_item("_title", &section.title).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _title: {}", e)))?;
        section_dict.set_item("_description", &section.description).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _description: {}", e)))?;
        section_dict.set_item("_order", section.order).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _order: {}", e)))?;

        for field in section.fields() {
            let field_dict = PyDict::new_bound(py);
            field_dict.set_item("_type", field.field_type().as_str()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _type: {}", e)))?;
            field_dict.set_item("_display", field.display_name()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _display: {}", e)))?;
            field_dict.set_item("_required", field.is_required()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _required: {}", e)))?;
            field_dict.set_item("_requirement", field.requirement().as_str()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _requirement: {}", e)))?;

            if !field.description().is_empty() {
                field_dict.set_item("_description", field.description()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _description: {}", e)))?;
            }

            if !field.condition().is_empty() {
                field_dict.set_item("_condition", field.condition()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _condition: {}", e)))?;
            }

            // Set value: default if present, null otherwise
            match field.default_value() {
                Some(val) => field_dict.set_item("value", val).map_err(|e| PyRuntimeError::new_err(format!("Failed to set value: {}", e)))?,
                None => field_dict.set_item("value", py.None()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set value: {}", e)))?,
            }

            // Type-specific metadata
            if field.field_type() == TemplateFieldType::Enum && !field.enum_variants().is_empty() {
                field_dict.set_item("_enum_variants", field.enum_variants()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _enum_variants: {}", e)))?;
            }
            if field.field_type() == TemplateFieldType::Reference && !field.reference_entity().is_empty() {
                field_dict.set_item("_reference_entity", field.reference_entity()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _reference_entity: {}", e)))?;
            }
            if field.field_type() == TemplateFieldType::File && !field.file_accept().is_empty() {
                field_dict.set_item("_file_accept", field.file_accept()).map_err(|e| PyRuntimeError::new_err(format!("Failed to set _file_accept: {}", e)))?;
            }

            section_dict.set_item(field.name(), field_dict).map_err(|e| PyRuntimeError::new_err(format!("Failed to set field {}: {}", field.name(), e)))?;
            total_fields += 1;
        }

        sections.set_item(section.section_id(), section_dict).map_err(|e| PyRuntimeError::new_err(format!("Failed to set section {}: {}", section.section_id(), e)))?;
    }

    template.set_item("sections", sections).map_err(|e| PyRuntimeError::new_err(format!("Failed to set sections: {}", e)))?;

    // ── Completeness ────────────────────────────────────────
    let completeness = PyDict::new_bound(py);
    let required_count = niche.required_field_count();
    completeness.set_item("total_fields", total_fields).map_err(|e| PyRuntimeError::new_err(format!("Failed to set total_fields: {}", e)))?;
    completeness.set_item("filled_fields", 0).map_err(|e| PyRuntimeError::new_err(format!("Failed to set filled_fields: {}", e)))?;
    completeness.set_item("missing_required", required_count).map_err(|e| PyRuntimeError::new_err(format!("Failed to set missing_required: {}", e)))?;
    let pct = if total_fields > 0 { 0.0_f64 } else { 100.0_f64 };
    completeness.set_item("completion_pct", pct).map_err(|e| PyRuntimeError::new_err(format!("Failed to set completion_pct: {}", e)))?;
    completeness.set_item("status", "incomplete").map_err(|e| PyRuntimeError::new_err(format!("Failed to set status: {}", e)))?;

    template.set_item("completeness", completeness).map_err(|e| PyRuntimeError::new_err(format!("Failed to set completeness: {}", e)))?;
    root.set_item("template", template).map_err(|e| PyRuntimeError::new_err(format!("Failed to set template: {}", e)))?;

    Ok(root.unbind())
}
