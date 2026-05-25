// ─── Zenic-Agents v3 — Template Constraints ───────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Template Constraints
//
// Provides constraint validation for policy templates.
// Each constraint type has its own validation logic.
// Complements the instantiateTemplate function in types.ts.
//
// Design Patterns:
//   - Strategy: Pluggable constraint validation strategies
//   - Validator: ConstraintValidator enforces cross-parameter constraint rules

import type {
  TemplateConstraint,
  TemplateParameter,
  TemplateConstraintType,
} from "./types";

// ─── Constraint Validation Result ─────────────────────────────────────

/**
 * Result of constraint validation.
 */
export interface ConstraintValidationResult {
  valid: boolean;
  errors: string[];
}

// ─── Constraint Validation ────────────────────────────────────────────

/**
 * Validate all constraint rules against resolved parameter values.
 * Each constraint type has its own validation logic.
 */
export function validateConstraints(
  constraints: TemplateConstraint[],
  resolvedParams: Record<string, unknown>,
): ConstraintValidationResult {
  const errors: string[] = [];

  for (const constraint of constraints) {
    switch (constraint.type) {
      case "mutually_exclusive": {
        const params = constraint.parameters.parameters as string[];
        if (!Array.isArray(params) || params.length < 2) {
          errors.push(`Constraint "${constraint.name}": mutually_exclusive requires at least 2 parameters`);
          break;
        }
        const param0 = params[0]!;
        const param1 = params[1]!;
        const hasParam0 = param0 in resolvedParams && resolvedParams[param0] !== undefined && resolvedParams[param0] !== null;
        const hasParam1 = param1 in resolvedParams && resolvedParams[param1] !== undefined && resolvedParams[param1] !== null;
        if (hasParam0 && hasParam1) {
          errors.push(constraint.errorMessage || `Parameters "${param0}" and "${param1}" are mutually exclusive`);
        }
        break;
      }

      case "requires": {
        const params = constraint.parameters.parameters as string[];
        if (!Array.isArray(params) || params.length < 2) {
          errors.push(`Constraint "${constraint.name}": requires constraint needs at least 2 parameters`);
          break;
        }
        const param0 = params[0]!;
        const param1 = params[1]!;
        const hasParam0 = param0 in resolvedParams && resolvedParams[param0] !== undefined && resolvedParams[param0] !== null;
        const hasParam1 = param1 in resolvedParams && resolvedParams[param1] !== undefined && resolvedParams[param1] !== null;
        if (hasParam0 && !hasParam1) {
          errors.push(constraint.errorMessage || `Parameter "${param0}" requires "${param1}" to also be set`);
        }
        break;
      }

      case "range_constraint": {
        const paramName = constraint.parameters.parameter as string;
        const min = constraint.parameters.min as number | undefined;
        const max = constraint.parameters.max as number | undefined;
        const value = resolvedParams[paramName];

        if (value !== undefined && value !== null && typeof value === "number") {
          if (min !== undefined && value < min) {
            errors.push(constraint.errorMessage || `Parameter "${paramName}" value ${value} is below minimum ${min}`);
          }
          if (max !== undefined && value > max) {
            errors.push(constraint.errorMessage || `Parameter "${paramName}" value ${value} exceeds maximum ${max}`);
          }
        }
        break;
      }

      case "regex_constraint": {
        const paramName = constraint.parameters.parameter as string;
        const pattern = constraint.parameters.regex as string;
        const value = resolvedParams[paramName];

        if (value !== undefined && value !== null && typeof value === "string") {
          try {
            const regex = new RegExp(pattern);
            if (!regex.test(value)) {
              errors.push(constraint.errorMessage || `Parameter "${paramName}" value "${value}" does not match regex "${pattern}"`);
            }
          } catch {
            errors.push(`Constraint "${constraint.name}": invalid regex pattern "${pattern}"`);
          }
        }
        break;
      }

      case "custom_expression": {
        const expression = constraint.parameters.expression as string;
        if (typeof expression !== "string") {
          errors.push(`Constraint "${constraint.name}": custom_expression requires an expression string`);
          break;
        }
        const result = evaluateCustomExpression(expression, resolvedParams);
        if (!result) {
          errors.push(constraint.errorMessage || `Custom expression "${expression}" evaluated to false`);
        }
        break;
      }

      default:
        errors.push(`Unknown constraint type "${constraint.type}" on constraint "${constraint.name}"`);
    }
  }

  return { valid: errors.length === 0, errors };
}

// ─── Custom Expression Evaluation ──────────────────────────────────────

/**
 * Evaluate a simple custom boolean expression.
 * Supports basic comparisons: param1 == "value", param1 != "value",
 * param1 > 10, param1 < 10, param1 >= 10, param1 <= 10
 * AND logical operators: expr1 && expr2
 */
export function evaluateCustomExpression(
  expression: string,
  resolvedParams: Record<string, unknown>,
): boolean {
  const parts = expression.split("&&").map((s) => s.trim());

  return parts.every((part) => {
    const compMatch = part.match(/^(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)$/);
    if (!compMatch) return false;

    const [, paramName, operator, rawValue] = compMatch;
    const paramValue = resolvedParams[paramName!];

    let compValue: unknown = rawValue!.trim();
    const trimmed = rawValue!.trim();

    if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
      compValue = parseFloat(trimmed);
    } else if (trimmed === "true") {
      compValue = true;
    } else if (trimmed === "false") {
      compValue = false;
    } else if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      compValue = trimmed.slice(1, -1);
    }

    switch (operator) {
      case "==": return paramValue == compValue;
      case "!=": return paramValue != compValue;
      case ">": return typeof paramValue === "number" && typeof compValue === "number" && paramValue > compValue;
      case "<": return typeof paramValue === "number" && typeof compValue === "number" && paramValue < compValue;
      case ">=": return typeof paramValue === "number" && typeof compValue === "number" && paramValue >= compValue;
      case "<=": return typeof paramValue === "number" && typeof compValue === "number" && paramValue <= compValue;
      default: return false;
    }
  });
}

// ─── Constraint Type Validation ───────────────────────────────────────

const VALID_CONSTRAINT_TYPES: ReadonlySet<string> = new Set([
  "mutually_exclusive",
  "requires",
  "range_constraint",
  "regex_constraint",
  "custom_expression",
]);

/**
 * Validate that a constraint type string is recognized.
 */
export function isValidConstraintType(type: string): type is TemplateConstraintType {
  return VALID_CONSTRAINT_TYPES.has(type);
}

/**
 * Validate a single constraint definition.
 */
export function validateConstraintDefinition(
  constraint: TemplateConstraint,
): ConstraintValidationResult {
  const errors: string[] = [];

  if (!constraint.name || typeof constraint.name !== "string") {
    errors.push("Constraint name is required and must be a string");
  }

  if (!constraint.type || !VALID_CONSTRAINT_TYPES.has(constraint.type)) {
    errors.push(`Constraint type must be one of: ${[...VALID_CONSTRAINT_TYPES].join(", ")}`);
  }

  if (!constraint.parameters || typeof constraint.parameters !== "object") {
    errors.push("Constraint parameters is required and must be an object");
  }

  if (!constraint.errorMessage || typeof constraint.errorMessage !== "string") {
    errors.push("Constraint errorMessage is required and must be a string");
  }

  // Type-specific validation
  if (constraint.type === "mutually_exclusive" || constraint.type === "requires") {
    const params = constraint.parameters?.parameters;
    if (!Array.isArray(params) || params.length < 2) {
      errors.push(`Constraint "${constraint.name}": ${constraint.type} requires at least 2 parameter names`);
    }
  }

  if (constraint.type === "range_constraint") {
    if (!constraint.parameters?.parameter) {
      errors.push(`Constraint "${constraint.name}": range_constraint requires a "parameter" field`);
    }
  }

  if (constraint.type === "regex_constraint") {
    if (!constraint.parameters?.regex) {
      errors.push(`Constraint "${constraint.name}": regex_constraint requires a "regex" field`);
    } else {
      try {
        new RegExp(constraint.parameters.regex as string);
      } catch {
        errors.push(`Constraint "${constraint.name}": invalid regex pattern "${constraint.parameters.regex}"`);
      }
    }
  }

  if (constraint.type === "custom_expression") {
    if (!constraint.parameters?.expression) {
      errors.push(`Constraint "${constraint.name}": custom_expression requires an "expression" field`);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validate all constraint definitions in a template.
 */
export function validateAllConstraintDefinitions(
  constraints: TemplateConstraint[],
): ConstraintValidationResult {
  const allErrors: string[] = [];

  for (const constraint of constraints) {
    const result = validateConstraintDefinition(constraint);
    allErrors.push(...result.errors);
  }

  return { valid: allErrors.length === 0, errors: allErrors };
}
