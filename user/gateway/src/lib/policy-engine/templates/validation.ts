// ─── Zenic-Agents v3 — Template Validation ────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Template Validation
//
// Provides template structure validation: checks apiVersion, kind,
// metadata, parameters, documentTemplate, and constraints.
// Complements the createTemplate function in types.ts.
//
// Design Patterns:
//   - Validator: Template validation with detailed error reporting

import type {
  PolicyTemplate,
  TemplateParameter,
  TemplateParameterType,
  TemplateConstraintType,
  TemplateMetadata,
  PolicyDocumentTemplate,
  StatementTemplate,
} from "./types";

// ─── Validation Constants ─────────────────────────────────────────────

const VALID_PARAMETER_TYPES: ReadonlySet<string> = new Set([
  "string",
  "number",
  "boolean",
  "enum",
  "array",
  "object",
  "resource_pattern",
  "action_pattern",
]);

const VALID_CONSTRAINT_TYPES: ReadonlySet<string> = new Set([
  "mutually_exclusive",
  "requires",
  "range_constraint",
  "regex_constraint",
  "custom_expression",
]);

const VALID_EFFECTS: ReadonlySet<string> = new Set(["allow", "deny", "conditional"]);

// ─── Validation Result ────────────────────────────────────────────────

/**
 * Result of template validation.
 */
export interface TemplateValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// ─── Template Structure Validation ────────────────────────────────────

/**
 * Validate the structure of a PolicyTemplate object.
 * Checks: apiVersion, kind, metadata, parameters, documentTemplate, constraints.
 * Returns an array of error strings (empty = valid).
 */
export function validateTemplateStructure(template: PolicyTemplate): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // apiVersion
  if (template.apiVersion !== "template.zenic.dev/v1") {
    errors.push(`Invalid apiVersion "${template.apiVersion}". Expected "template.zenic.dev/v1"`);
  }

  // kind
  if (template.kind !== "PolicyTemplate") {
    errors.push(`Invalid kind "${template.kind}". Expected "PolicyTemplate"`);
  }

  // metadata
  const metadataResult = validateTemplateMetadata(template.metadata);
  errors.push(...metadataResult.errors);
  warnings.push(...metadataResult.warnings);

  // parameters
  const paramsResult = validateTemplateParameters(template.parameters);
  errors.push(...paramsResult.errors);
  warnings.push(...paramsResult.warnings);

  // documentTemplate
  const docResult = validateDocumentTemplate(template.documentTemplate);
  errors.push(...docResult.errors);
  warnings.push(...docResult.warnings);

  // constraints (optional)
  if (template.constraints && Array.isArray(template.constraints)) {
    const constraintResult = validateTemplateConstraints(template.constraints);
    errors.push(...constraintResult.errors);
    warnings.push(...constraintResult.warnings);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ─── Metadata Validation ──────────────────────────────────────────────

/**
 * Validate template metadata.
 */
export function validateTemplateMetadata(metadata: TemplateMetadata): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!metadata) {
    errors.push("metadata is required");
    return { valid: false, errors, warnings };
  }

  if (!metadata.id || typeof metadata.id !== "string") {
    errors.push("metadata.id is required and must be a string");
  }

  if (!metadata.name || typeof metadata.name !== "string") {
    errors.push("metadata.name is required and must be a string");
  }

  if (!metadata.version || typeof metadata.version !== "string") {
    errors.push("metadata.version is required and must be a string");
  } else if (!/^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/.test(metadata.version)) {
    warnings.push(`Invalid semver format: "${metadata.version}"`);
  }

  if (!metadata.description || typeof metadata.description !== "string") {
    errors.push("metadata.description is required and must be a string");
  }

  if (!metadata.category || typeof metadata.category !== "string") {
    errors.push("metadata.category is required and must be a string");
  }

  return { valid: errors.length === 0, errors, warnings };
}

// ─── Parameters Validation ────────────────────────────────────────────

/**
 * Validate template parameter definitions.
 */
export function validateTemplateParameters(
  parameters: TemplateParameter[],
): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(parameters)) {
    errors.push("parameters must be an array");
    return { valid: false, errors, warnings };
  }

  const paramNames = new Set<string>();

  for (let i = 0; i < parameters.length; i++) {
    const param = parameters[i]!;
    const prefix = `parameters[${i}]`;

    if (!param.name || typeof param.name !== "string") {
      errors.push(`${prefix}.name is required and must be a string`);
    } else {
      if (paramNames.has(param.name)) {
        errors.push(`${prefix}.name "${param.name}" is duplicated — parameter names must be unique`);
      }
      paramNames.add(param.name);
    }

    if (!param.displayName || typeof param.displayName !== "string") {
      errors.push(`${prefix}.displayName is required`);
    }

    if (!param.description || typeof param.description !== "string") {
      errors.push(`${prefix}.description is required`);
    }

    if (!param.type || !VALID_PARAMETER_TYPES.has(param.type)) {
      errors.push(`${prefix}.type must be one of: ${[...VALID_PARAMETER_TYPES].join(", ")}`);
    }

    if (param.type === "enum" && (!param.allowedValues || param.allowedValues.length === 0)) {
      errors.push(`${prefix}.allowedValues is required for ENUM type parameter "${param.name}"`);
    }

    if (typeof param.required !== "boolean") {
      errors.push(`${prefix}.required must be a boolean`);
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

// ─── Document Template Validation ─────────────────────────────────────

/**
 * Validate the document template structure.
 */
export function validateDocumentTemplate(
  doc: PolicyDocumentTemplate,
): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!doc) {
    errors.push("documentTemplate is required");
    return { valid: false, errors, warnings };
  }

  if (!doc.name || typeof doc.name !== "string") {
    errors.push("documentTemplate.name is required and must be a string");
  }

  if (!doc.description || typeof doc.description !== "string") {
    errors.push("documentTemplate.description is required and must be a string");
  }

  if (!Array.isArray(doc.statements) || doc.statements.length === 0) {
    errors.push("documentTemplate.statements must be a non-empty array");
  } else {
    for (let i = 0; i < doc.statements.length; i++) {
      const stmt = doc.statements[i]!;
      const prefix = `documentTemplate.statements[${i}]`;

      const stmtResult = validateStatementTemplate(stmt, prefix);
      errors.push(...stmtResult.errors);
      warnings.push(...stmtResult.warnings);
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

/**
 * Validate a single statement template.
 */
export function validateStatementTemplate(
  stmt: StatementTemplate,
  prefix: string,
): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!stmt.id || typeof stmt.id !== "string") {
    errors.push(`${prefix}.id is required`);
  }

  if (!stmt.effect || !VALID_EFFECTS.has(stmt.effect)) {
    errors.push(`${prefix}.effect must be one of: ${[...VALID_EFFECTS].join(", ")}`);
  }

  if (!stmt.resource || typeof stmt.resource !== "string") {
    errors.push(`${prefix}.resource is required`);
  }

  if (!stmt.action || typeof stmt.action !== "string") {
    errors.push(`${prefix}.action is required`);
  }

  return { valid: errors.length === 0, errors, warnings };
}

// ─── Constraints Validation ───────────────────────────────────────────

/**
 * Validate template constraint definitions.
 */
export function validateTemplateConstraints(
  constraints: Array<{
    name: string;
    type: string;
    parameters: Record<string, unknown>;
    errorMessage: string;
  }>,
): TemplateValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  for (let i = 0; i < constraints.length; i++) {
    const constraint = constraints[i]!;
    const prefix = `constraints[${i}]`;

    if (!constraint.name || typeof constraint.name !== "string") {
      errors.push(`${prefix}.name is required`);
    }

    if (!constraint.type || !VALID_CONSTRAINT_TYPES.has(constraint.type)) {
      errors.push(`${prefix}.type must be one of: ${[...VALID_CONSTRAINT_TYPES].join(", ")}`);
    }

    if (!constraint.parameters || typeof constraint.parameters !== "object") {
      errors.push(`${prefix}.parameters is required and must be an object`);
    }

    if (!constraint.errorMessage || typeof constraint.errorMessage !== "string") {
      errors.push(`${prefix}.errorMessage is required`);
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

// ─── Utility ──────────────────────────────────────────────────────────

/**
 * Check if a parameter type string is valid.
 */
export function isValidParameterType(type: string): type is TemplateParameterType {
  return VALID_PARAMETER_TYPES.has(type);
}

/**
 * Check if a constraint type string is valid.
 */
export function isValidConstraintType(type: string): type is TemplateConstraintType {
  return VALID_CONSTRAINT_TYPES.has(type);
}

/**
 * Quick check if a template appears structurally valid.
 * Returns true if no critical errors are found.
 */
export function isTemplateValid(template: PolicyTemplate): boolean {
  return validateTemplateStructure(template).valid;
}
