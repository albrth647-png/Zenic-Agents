// ─── Zenic-Agents v3 — Policy Composition Validators ─────────────────
// Phase 4: Declarative Versioned Policy Engine — Validation Utilities
//
// Provides validation functions for policy sets, merge strategies,
// and composition inputs. Complements the CompositionEngine in types.ts.

import type {
  PolicySet,
  PolicySetEntry,
  MergeStrategy,
  PolicyDocument,
  PolicyStatement,
  PolicyEffectV2,
} from "./types";

// ─── Merge Strategy Validation ────────────────────────────────────────

const VALID_MERGE_STRATEGIES: ReadonlySet<string> = new Set([
  "union",
  "intersection",
  "override",
  "extend",
  "priority_merge",
]);

const VALID_EFFECTS: ReadonlySet<string> = new Set(["allow", "deny", "conditional"]);

/**
 * Validate that a merge strategy string is recognized.
 * Returns the validated strategy or throws.
 */
export function validateMergeStrategy(strategy: string): MergeStrategy {
  if (!VALID_MERGE_STRATEGIES.has(strategy)) {
    throw new Error(
      `Invalid merge strategy "${strategy}". Must be one of: ${[...VALID_MERGE_STRATEGIES].join(", ")}`,
    );
  }
  return strategy as MergeStrategy;
}

// ─── PolicySet Validation ─────────────────────────────────────────────

/**
 * Validation result for a PolicySet.
 */
export interface PolicySetValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validate a PolicySet object structure and content.
 * Checks apiVersion, kind, metadata, policies, and merge strategy.
 */
export function validatePolicySet(set: PolicySet): PolicySetValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // apiVersion
  if (!set.apiVersion || typeof set.apiVersion !== "string") {
    errors.push("apiVersion is required and must be a string");
  }

  // kind
  if (!set.kind || typeof set.kind !== "string") {
    errors.push("kind is required and must be a string");
  }

  // metadata
  if (!set.metadata) {
    errors.push("metadata is required");
  } else {
    if (!set.metadata.id || typeof set.metadata.id !== "string") {
      errors.push("metadata.id is required and must be a string");
    }
    if (!set.metadata.name || typeof set.metadata.name !== "string") {
      errors.push("metadata.name is required and must be a string");
    }
    if (!set.metadata.version || typeof set.metadata.version !== "string") {
      warnings.push("metadata.version should be a valid semver string");
    }
  }

  // policies
  if (!Array.isArray(set.policies)) {
    errors.push("policies must be an array");
  } else {
    const policyIds = new Set<string>();
    for (let i = 0; i < set.policies.length; i++) {
      const entry = set.policies[i]!;
      const prefix = `policies[${i}]`;

      const entryResult = validatePolicySetEntry(entry, prefix);
      errors.push(...entryResult.errors);
      warnings.push(...entryResult.warnings);

      // Check for duplicate policyId+version
      const key = `${entry.policyId}@${entry.version ?? "latest"}`;
      if (policyIds.has(key)) {
        warnings.push(`${prefix}: duplicate policy reference "${key}"`);
      }
      policyIds.add(key);
    }
  }

  // defaultMergeStrategy
  if (!set.defaultMergeStrategy || !VALID_MERGE_STRATEGIES.has(set.defaultMergeStrategy)) {
    errors.push(
      `defaultMergeStrategy must be one of: ${[...VALID_MERGE_STRATEGIES].join(", ")}`,
    );
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate a single PolicySetEntry.
 */
export function validatePolicySetEntry(
  entry: PolicySetEntry,
  prefix: string = "entry",
): PolicySetValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!entry.policyId || typeof entry.policyId !== "string") {
    errors.push(`${prefix}.policyId is required and must be a string`);
  }

  if (entry.version !== undefined && typeof entry.version !== "string") {
    errors.push(`${prefix}.version must be a string if provided`);
  }

  if (typeof entry.required !== "boolean") {
    warnings.push(`${prefix}.required should be a boolean (defaulting to false)`);
  }

  if (entry.priority !== undefined && typeof entry.priority !== "number") {
    errors.push(`${prefix}.priority must be a number if provided`);
  }

  if (entry.priority !== undefined && entry.priority < 0) {
    warnings.push(`${prefix}.priority is negative — this may cause unexpected ordering`);
  }

  // Validate overrides
  if (entry.overrides && Array.isArray(entry.overrides)) {
    for (let i = 0; i < entry.overrides.length; i++) {
      const override = entry.overrides[i]!;
      if (!override.id || typeof override.id !== "string") {
        errors.push(`${prefix}.overrides[${i}].id is required`);
      }
      if (override.effect && !VALID_EFFECTS.has(override.effect)) {
        errors.push(`${prefix}.overrides[${i}].effect must be one of: ${[...VALID_EFFECTS].join(", ")}`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ─── PolicyDocument Validation ────────────────────────────────────────

/**
 * Validate a PolicyDocument structure.
 */
export function validatePolicyDocument(doc: PolicyDocument): PolicySetValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!doc.apiVersion || typeof doc.apiVersion !== "string") {
    errors.push("apiVersion is required");
  }

  if (!doc.kind || doc.kind !== "PolicyDocument") {
    errors.push('kind must be "PolicyDocument"');
  }

  if (!doc.metadata) {
    errors.push("metadata is required");
  } else {
    if (!doc.metadata.id) errors.push("metadata.id is required");
    if (!doc.metadata.name) errors.push("metadata.name is required");
    if (!doc.metadata.version) warnings.push("metadata.version is missing");
  }

  if (!Array.isArray(doc.statements)) {
    errors.push("statements must be an array");
  } else {
    for (let i = 0; i < doc.statements.length; i++) {
      const stmt = doc.statements[i]!;
      const prefix = `statements[${i}]`;
      const stmtResult = validateStatement(stmt, prefix);
      errors.push(...stmtResult.errors);
      warnings.push(...stmtResult.warnings);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate a single PolicyStatement.
 */
export function validateStatement(
  stmt: PolicyStatement,
  prefix: string = "statement",
): PolicySetValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!stmt.id || typeof stmt.id !== "string") {
    errors.push(`${prefix}.id is required and must be a string`);
  }

  if (!stmt.effect || !VALID_EFFECTS.has(stmt.effect)) {
    errors.push(`${prefix}.effect must be one of: ${[...VALID_EFFECTS].join(", ")}`);
  }

  if (!stmt.resource || typeof stmt.resource !== "string") {
    errors.push(`${prefix}.resource is required and must be a string`);
  }

  if (!stmt.action || typeof stmt.action !== "string") {
    errors.push(`${prefix}.action is required and must be a string`);
  }

  if (typeof stmt.priority !== "number") {
    errors.push(`${prefix}.priority must be a number`);
  }

  if (stmt.priority < 0) {
    warnings.push(`${prefix}.priority is negative — may cause unexpected ordering`);
  }

  // Validate conditions
  if (stmt.conditions && Array.isArray(stmt.conditions)) {
    for (let i = 0; i < stmt.conditions.length; i++) {
      const cond = stmt.conditions[i]!;
      if (!cond.field || typeof cond.field !== "string") {
        errors.push(`${prefix}.conditions[${i}].field is required`);
      }
      if (!cond.operator || typeof cond.operator !== "string") {
        errors.push(`${prefix}.conditions[${i}].operator is required`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ─── Composition Input Validation ─────────────────────────────────────

/**
 * Validate that a set of policy statements can be composed.
 * Checks for empty inputs, valid effects, and statement integrity.
 */
export function validateCompositionInput(
  policyStatementArrays: PolicyStatement[][],
): PolicySetValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (policyStatementArrays.length === 0) {
    warnings.push("No policy statements to compose — result will be empty");
  }

  let totalStatements = 0;
  for (let i = 0; i < policyStatementArrays.length; i++) {
    const stmts = policyStatementArrays[i]!;
    if (!Array.isArray(stmts)) {
      errors.push(`Policy at index ${i} does not have a valid statements array`);
      continue;
    }
    totalStatements += stmts.length;

    for (let j = 0; j < stmts.length; j++) {
      const stmt = stmts[j]!;
      if (!stmt.id) {
        errors.push(`Policy ${i}, statement ${j}: missing id`);
      }
      if (!stmt.effect || !VALID_EFFECTS.has(stmt.effect)) {
        errors.push(`Policy ${i}, statement ${j}: invalid effect "${stmt.effect}"`);
      }
    }
  }

  if (totalStatements === 0 && policyStatementArrays.length > 0) {
    warnings.push("All policies have empty statement arrays");
  }

  if (totalStatements > 10000) {
    warnings.push(`Large composition (${totalStatements} statements) — may be slow`);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}
