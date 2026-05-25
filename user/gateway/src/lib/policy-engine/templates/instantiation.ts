// ─── Zenic-Agents v3 — Template Instantiation ─────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Template Instantiation
//
// Provides template instantiation logic: parameter resolution,
// default value application, and auto-deployment.
// Complements the instantiateTemplate function in types.ts.
//
// Design Patterns:
//   - Builder: Constructs instantiated PolicyDocument from template + params
//   - Interpreter: Variable substitution during instantiation

import { db } from "@/lib/db";
import { computeContentHash } from "../yaml-loader";
import { POLICY_API_VERSION } from "../types";
import type {
  PolicyDocument,
  PolicyStatement,
  PolicyEffectV2,
} from "../types";
import type {
  TemplateParameter,
  TemplateInstantiationRequest,
  TemplateInstantiationResult,
  TemplateParameterType,
} from "./types";
import { substituteVariables, hasUnresolvedVariables, PolicyDocumentBuilder } from "./engine";
import { validateConstraints } from "./constraints";

// ─── Parameter Type Validation ────────────────────────────────────────

/** Validation result for a single parameter */
interface ParameterValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validate a single parameter value against its type definition.
 */
export function validateParameterType(
  value: unknown,
  param: TemplateParameter,
): ParameterValidationResult {
  switch (param.type) {
    case "string" as TemplateParameterType:
      if (typeof value !== "string") {
        return { valid: false, error: `Parameter "${param.name}" must be a string, got ${typeof value}` };
      }
      if (param.validationRegex) {
        try {
          const regex = new RegExp(param.validationRegex);
          if (!regex.test(value)) {
            return { valid: false, error: `Parameter "${param.name}" value "${value}" does not match regex "${param.validationRegex}"` };
          }
        } catch {
          return { valid: false, error: `Parameter "${param.name}" has invalid validationRegex "${param.validationRegex}"` };
        }
      }
      return { valid: true };

    case "number" as TemplateParameterType:
      if (typeof value !== "number" || isNaN(value)) {
        return { valid: false, error: `Parameter "${param.name}" must be a number, got ${typeof value}` };
      }
      if (param.minValue !== undefined && value < param.minValue) {
        return { valid: false, error: `Parameter "${param.name}" value ${value} is below minimum ${param.minValue}` };
      }
      if (param.maxValue !== undefined && value > param.maxValue) {
        return { valid: false, error: `Parameter "${param.name}" value ${value} exceeds maximum ${param.maxValue}` };
      }
      return { valid: true };

    case "boolean" as TemplateParameterType:
      if (typeof value !== "boolean") {
        return { valid: false, error: `Parameter "${param.name}" must be a boolean, got ${typeof value}` };
      }
      return { valid: true };

    case "enum" as TemplateParameterType:
      if (!param.allowedValues || param.allowedValues.length === 0) {
        return { valid: false, error: `Parameter "${param.name}" has no allowedValues defined for enum type` };
      }
      if (!param.allowedValues.includes(value)) {
        return { valid: false, error: `Parameter "${param.name}" value "${String(value)}" is not in allowed values: [${param.allowedValues.map(String).join(", ")}]` };
      }
      return { valid: true };

    case "array" as TemplateParameterType:
      if (!Array.isArray(value)) {
        return { valid: false, error: `Parameter "${param.name}" must be an array, got ${typeof value}` };
      }
      return { valid: true };

    case "object" as TemplateParameterType:
      if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return { valid: false, error: `Parameter "${param.name}" must be an object, got ${value === null ? "null" : Array.isArray(value) ? "array" : typeof value}` };
      }
      return { valid: true };

    case "resource_pattern" as TemplateParameterType:
      if (typeof value !== "string") {
        return { valid: false, error: `Parameter "${param.name}" must be a string for resource_pattern, got ${typeof value}` };
      }
      if (/\s/.test(value)) {
        return { valid: false, error: `Parameter "${param.name}" resource_pattern "${value}" must not contain spaces` };
      }
      return { valid: true };

    case "action_pattern" as TemplateParameterType:
      if (typeof value !== "string") {
        return { valid: false, error: `Parameter "${param.name}" must be a string for action_pattern, got ${typeof value}` };
      }
      if (/\s/.test(value)) {
        return { valid: false, error: `Parameter "${param.name}" action_pattern "${value}" must not contain spaces` };
      }
      return { valid: true };

    default:
      return { valid: false, error: `Unknown parameter type "${param.type}" for parameter "${param.name}"` };
  }
}

// ─── Parameter Resolution ─────────────────────────────────────────────

/**
 * Resolve all parameters for a template instantiation.
 * Applies defaults, validates required parameters, and returns resolved values.
 */
export function resolveParameters(
  template: {
    parameters: TemplateParameter[];
    defaults: Record<string, unknown>;
  },
  providedParams: Record<string, unknown>,
): {
  resolved: Record<string, unknown>;
  errors: string[];
  warnings: string[];
  unresolvedParameters: string[];
} {
  const resolved: Record<string, unknown> = {};
  const errors: string[] = [];
  const warnings: string[] = [];
  const unresolvedParameters: string[] = [];

  for (const param of template.parameters) {
    if (param.name in providedParams && providedParams[param.name] !== undefined && providedParams[param.name] !== null) {
      resolved[param.name] = providedParams[param.name];
    } else if (param.defaultValue !== undefined) {
      resolved[param.name] = param.defaultValue;
      warnings.push(`Parameter "${param.name}" using default value: ${JSON.stringify(param.defaultValue)}`);
    } else if (template.defaults[param.name] !== undefined) {
      resolved[param.name] = template.defaults[param.name];
      warnings.push(`Parameter "${param.name}" using default from defaults map: ${JSON.stringify(template.defaults[param.name])}`);
    } else if (param.required) {
      unresolvedParameters.push(param.name);
      errors.push(`Required parameter "${param.name}" has no value`);
    }
  }

  return { resolved, errors, warnings, unresolvedParameters };
}

// ─── Instantiation ────────────────────────────────────────────────────

/**
 * Instantiate a template with the given parameters.
 * This is a standalone function that doesn't depend on DB.
 * Returns the instantiated PolicyDocument without persisting.
 */
export async function instantiateFromTemplate(
  template: {
    metadata: { id: string; version: string; author?: string };
    parameters: TemplateParameter[];
    documentTemplate: import("./types").PolicyDocumentTemplate;
    defaults: Record<string, unknown>;
    constraints: import("./types").TemplateConstraint[];
  },
  request: {
    parameters: Record<string, unknown>;
  },
): Promise<TemplateInstantiationResult> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const unresolvedParameters: string[] = [];

  // 1. Resolve parameters
  const { resolved, errors: resolveErrors, warnings: resolveWarnings, unresolvedParameters: unresolved } = resolveParameters(template, request.parameters);
  errors.push(...resolveErrors);
  warnings.push(...resolveWarnings);
  unresolvedParameters.push(...unresolved);

  if (errors.length > 0) {
    return {
      success: false,
      errors,
      warnings,
      unresolvedParameters,
    };
  }

  // 2. Validate parameter types
  for (const param of template.parameters) {
    if (param.name in resolved) {
      const result = validateParameterType(resolved[param.name], param);
      if (!result.valid) {
        errors.push(result.error!);
      }
    }
  }

  if (errors.length > 0) {
    return {
      success: false,
      errors,
      warnings,
      unresolvedParameters,
    };
  }

  // 3. Validate constraints
  const constraintResult = validateConstraints(template.constraints, resolved);
  if (!constraintResult.valid) {
    errors.push(...constraintResult.errors);
  }

  if (errors.length > 0) {
    return {
      success: false,
      errors,
      warnings,
      unresolvedParameters,
    };
  }

  // 4. Build PolicyDocument
  const builder = new PolicyDocumentBuilder(
    template.documentTemplate,
    resolved,
    template.metadata as import("./types").TemplateMetadata,
  );
  const document = builder.build();

  // 5. Check for unresolved variables
  const docString = JSON.stringify(document);
  const remainingVars = hasUnresolvedVariables(docString);
  if (remainingVars.length > 0) {
    const uniqueVars = [...new Set(remainingVars)];
    warnings.push(`Unresolved variables remain in generated document: ${uniqueVars.join(", ")}`);
  }

  return {
    success: true,
    document,
    errors,
    warnings,
    unresolvedParameters: [],
  };
}

// ─── Auto-Deploy ──────────────────────────────────────────────────────

/**
 * Auto-deploy an instantiated policy document to the database.
 * Creates or updates the policy in the DeclPolicy table.
 */
export async function autoDeployPolicy(
  document: PolicyDocument,
  targetPolicyId: string,
  requestedBy: string,
): Promise<{ policyId: string; created: boolean }> {
  const contentHash = computeContentHash(document);

  const existing = await db.declPolicy.findUnique({
    where: { policyId: targetPolicyId },
  });

  if (existing) {
    await db.declPolicy.update({
      where: { policyId: targetPolicyId },
      data: {
        name: document.metadata.name,
        description: document.metadata.description,
        version: document.metadata.version,
        labels: JSON.stringify(document.metadata.labels ?? {}),
        compliance: JSON.stringify(document.metadata.compliance ?? []),
        statements: JSON.stringify(document.statements),
        tests: JSON.stringify(document.tests ?? []),
        contentHash,
        author: requestedBy,
      },
    });

    return { policyId: targetPolicyId, created: false };
  }

  await db.declPolicy.create({
    data: {
      policyId: targetPolicyId,
      name: document.metadata.name,
      description: document.metadata.description,
      apiVersion: POLICY_API_VERSION,
      version: document.metadata.version,
      labels: JSON.stringify(document.metadata.labels ?? {}),
      compliance: JSON.stringify(document.metadata.compliance ?? []),
      statements: JSON.stringify(document.statements),
      tests: JSON.stringify(document.tests ?? []),
      isActive: true,
      contentHash,
      author: requestedBy,
    },
  });

  return { policyId: targetPolicyId, created: true };
}

/**
 * Increment the template's generatedCount in the DB.
 */
export async function incrementGeneratedCount(templateId: string): Promise<void> {
  try {
    await db.policyTemplate.update({
      where: { templateId },
      data: {
        generatedCount: { increment: 1 },
      },
    });
  } catch (error) {
    console.warn(`Failed to increment generatedCount for template "${templateId}": ${error instanceof Error ? error.message : String(error)}`);
  }
}
