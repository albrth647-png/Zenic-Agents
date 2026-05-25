// ─── Zenic-Agents v3 — Conflict Analyzer ──────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Conflict Analysis
//
// Provides pattern-matching and condition-overlap analysis utilities
// for conflict detection. Complements the ConflictDetector in types.ts.
//
// Design Patterns:
//   - Visitor: analysis traversal of policy statements
//   - Strategy: pluggable condition comparison strategies

import type {
  PolicyStatement,
  PolicyCondition,
  PolicyEffectV2,
  ConflictStatementRef,
  ConflictType,
  ConflictSeverity,
} from "./types";

// ─── Pattern Matching ─────────────────────────────────────────────────

/**
 * Check if a concrete value matches a pattern.
 * Supports wildcard: "*" matches everything, "financial/*" matches "financial/transfer".
 */
export function matchesPattern(pattern: string, value: string): boolean {
  if (pattern === "*") return true;
  if (pattern === value) return true;

  // Wildcard suffix: "financial/*" → matches "financial/transfer"
  if (pattern.endsWith("/*")) {
    const prefix = pattern.slice(0, -2);
    return value === prefix || value.startsWith(`${prefix}/`);
  }

  // Wildcard prefix: "*/execute" → matches "financial/execute"
  if (pattern.startsWith("*/")) {
    const suffix = pattern.slice(1);
    return value.endsWith(suffix);
  }

  return false;
}

/**
 * Check if two resource/action patterns overlap.
 * Two patterns overlap if there exists at least one concrete value
 * that both could match. This is a conservative over-approximation.
 */
export function patternsOverlap(patternA: string, patternB: string): boolean {
  if (patternA === patternB) return true;
  if (patternA === "*" || patternB === "*") return true;

  if (patternA.endsWith("/*") && patternB.endsWith("/*")) {
    const prefixA = patternA.slice(0, -2);
    const prefixB = patternB.slice(0, -2);
    return prefixA === prefixB || prefixA.startsWith(`${prefixB}/`) || prefixB.startsWith(`${prefixA}/`);
  }

  if (patternA.endsWith("/*")) {
    const prefix = patternA.slice(0, -2);
    return patternB === prefix || patternB.startsWith(`${prefix}/`);
  }
  if (patternB.endsWith("/*")) {
    const prefix = patternB.slice(0, -2);
    return patternA === prefix || patternA.startsWith(`${prefix}/`);
  }

  if (patternA.startsWith("*/") && patternB.startsWith("*/")) {
    const suffixA = patternA.slice(1);
    const suffixB = patternB.slice(1);
    return suffixA.endsWith(suffixB) || suffixB.endsWith(suffixA) || suffixA === suffixB;
  }

  if (patternA.startsWith("*/")) {
    const suffix = patternA.slice(1);
    return patternB.endsWith(suffix);
  }
  if (patternB.startsWith("*/")) {
    const suffix = patternB.slice(1);
    return patternA.endsWith(suffix);
  }

  return false;
}

/**
 * Check if patternOuter contains patternInner.
 * E.g., "financial/*" contains "financial/transfer".
 */
export function patternContains(patternOuter: string, patternInner: string): boolean {
  if (patternOuter === "*") return true;
  if (patternOuter === patternInner) return true;

  if (patternOuter.endsWith("/*")) {
    const prefix = patternOuter.slice(0, -2);
    return patternInner === prefix || patternInner.startsWith(`${prefix}/`);
  }

  if (patternOuter.startsWith("*/")) {
    const suffix = patternOuter.slice(1);
    return patternInner.endsWith(suffix) || patternInner === suffix.slice(1);
  }

  return false;
}

/**
 * Check if two statements' resource/action patterns overlap.
 */
export function statementPatternsOverlap(a: PolicyStatement, b: PolicyStatement): boolean {
  return patternsOverlap(a.resource, b.resource) && patternsOverlap(a.action, b.action);
}

// ─── Condition Overlap Detection ──────────────────────────────────────

/**
 * Analysis result for condition overlap between two condition sets.
 */
export type ConditionOverlapResult =
  | "a_subset_b"   // A is more restrictive (B is more general)
  | "b_subset_a"   // B is more restrictive (A is more general)
  | "overlap"      // They overlap but neither is a subset
  | "disjoint"     // No overlap between the condition scopes
  | "equal";       // Conditions are equivalent

/**
 * Check if one condition set is a subset of another.
 * A condition set A is a subset of B if every request matching A
 * would also match B (B is more general or equal).
 */
export function analyzeConditionOverlap(
  conditionsA: PolicyCondition[] | undefined,
  conditionsB: PolicyCondition[] | undefined,
): ConditionOverlapResult {
  if ((!conditionsA || conditionsA.length === 0) && (!conditionsB || conditionsB.length === 0)) {
    return "equal";
  }

  if (!conditionsA || conditionsA.length === 0) {
    return "b_subset_a";
  }

  if (!conditionsB || conditionsB.length === 0) {
    return "a_subset_b";
  }

  const fieldsA = new Map<string, PolicyCondition[]>();
  const fieldsB = new Map<string, PolicyCondition[]>();

  for (const c of conditionsA) {
    const existing = fieldsA.get(c.field) ?? [];
    existing.push(c);
    fieldsA.set(c.field, existing);
  }
  for (const c of conditionsB) {
    const existing = fieldsB.get(c.field) ?? [];
    existing.push(c);
    fieldsB.set(c.field, existing);
  }

  let aSubsetB = true;
  let bSubsetA = true;
  let hasOverlap = true;

  for (const [field, condsA] of fieldsA) {
    const condsB = fieldsB.get(field);
    if (!condsB) {
      bSubsetA = false;
      continue;
    }
    const relation = compareFieldConditions(condsA, condsB);
    if (relation === "disjoint") {
      hasOverlap = false;
      aSubsetB = false;
      bSubsetA = false;
      break;
    }
    if (relation === "a_stricter") {
      bSubsetA = false;
    }
    if (relation === "b_stricter") {
      aSubsetB = false;
    }
    if (relation === "overlap") {
      aSubsetB = false;
      bSubsetA = false;
    }
  }

  for (const field of fieldsB.keys()) {
    if (!fieldsA.has(field)) {
      aSubsetB = false;
    }
  }

  if (!hasOverlap) return "disjoint";
  if (aSubsetB && bSubsetA) return "equal";
  if (aSubsetB) return "a_subset_b";
  if (bSubsetA) return "b_subset_a";
  return "overlap";
}

// ─── Field Condition Comparison ───────────────────────────────────────

type FieldComparisonResult = "a_stricter" | "b_stricter" | "equivalent" | "overlap" | "disjoint";

/**
 * Compare conditions on the same field.
 */
export function compareFieldConditions(
  condsA: PolicyCondition[],
  condsB: PolicyCondition[],
): FieldComparisonResult {
  const valuesA = condsA.map((c) => conditionSignature(c)).sort().join("|");
  const valuesB = condsB.map((c) => conditionSignature(c)).sort().join("|");

  if (valuesA === valuesB) return "equivalent";

  const eqValuesA = condsA.filter((c) => c.operator === "eq").map((c) => String(c.value));
  const eqValuesB = condsB.filter((c) => c.operator === "eq").map((c) => String(c.value));

  if (eqValuesA.length > 0 && eqValuesB.length > 0) {
    const intersection = eqValuesA.filter((v) => eqValuesB.includes(v));
    if (intersection.length === 0) return "disjoint";
  }

  if (condsA.length === 1 && condsB.length === 1) {
    const a = condsA[0]!;
    const b = condsB[0]!;
    return compareSingleConditions(a, b);
  }

  return "overlap";
}

/**
 * Compare two single conditions on the same field.
 */
export function compareSingleConditions(
  a: PolicyCondition,
  b: PolicyCondition,
): FieldComparisonResult {
  if (a.operator === b.operator && a.value === b.value) return "equivalent";

  if (a.operator === "eq" && b.operator === "in") {
    if (Array.isArray(b.value) && b.value.includes(a.value)) return "a_stricter";
    return "disjoint";
  }
  if (b.operator === "eq" && a.operator === "in") {
    if (Array.isArray(a.value) && a.value.includes(b.value)) return "b_stricter";
    return "disjoint";
  }

  if (a.operator === "eq" && b.operator === "eq") {
    return a.value === b.value ? "equivalent" : "disjoint";
  }

  // Numeric comparisons
  if ((a.operator === "gt" || a.operator === "gte") && (b.operator === "gt" || b.operator === "gte")) {
    const valA = typeof a.value === "number" ? a.value : NaN;
    const valB = typeof b.value === "number" ? b.value : NaN;
    if (isNaN(valA) || isNaN(valB)) return "overlap";
    const strictA = a.operator === "gt" ? valA : valA - 0.001;
    const strictB = b.operator === "gt" ? valB : valB - 0.001;
    if (strictA > strictB) return "b_stricter";
    if (strictB > strictA) return "a_stricter";
    return "equivalent";
  }

  if ((a.operator === "lt" || a.operator === "lte") && (b.operator === "lt" || b.operator === "lte")) {
    const valA = typeof a.value === "number" ? a.value : NaN;
    const valB = typeof b.value === "number" ? b.value : NaN;
    if (isNaN(valA) || isNaN(valB)) return "overlap";
    const strictA = a.operator === "lt" ? valA : valA + 0.001;
    const strictB = b.operator === "lt" ? valB : valB + 0.001;
    if (strictA < strictB) return "b_stricter";
    if (strictB < strictA) return "a_stricter";
    return "equivalent";
  }

  if ((a.operator === "gt" || a.operator === "gte") && (b.operator === "lt" || b.operator === "lte")) {
    const low = typeof a.value === "number" ? a.value : NaN;
    const high = typeof b.value === "number" ? b.value : NaN;
    if (!isNaN(low) && !isNaN(high) && low >= high) return "disjoint";
    return "overlap";
  }
  if ((a.operator === "lt" || a.operator === "lte") && (b.operator === "gt" || b.operator === "gte")) {
    const high = typeof a.value === "number" ? a.value : NaN;
    const low = typeof b.value === "number" ? b.value : NaN;
    if (!isNaN(low) && !isNaN(high) && low >= high) return "disjoint";
    return "overlap";
  }

  return "overlap";
}

/**
 * Generate a comparable signature for a condition.
 */
export function conditionSignature(c: PolicyCondition): string {
  return `${c.operator}:${JSON.stringify(c.value)}`;
}

// ─── Statement Containment ────────────────────────────────────────────

/**
 * Check if statement A is entirely contained by statement B.
 * A is contained by B if B's resource/action patterns are a superset
 * and B's conditions are a superset (less restrictive).
 */
export function isStatementContainedBy(a: PolicyStatement, b: PolicyStatement): boolean {
  if (!patternContains(b.resource, a.resource)) return false;
  if (!patternContains(b.action, a.action)) return false;

  const condRelation = analyzeConditionOverlap(a.conditions, b.conditions);
  return condRelation === "a_subset_b" || condRelation === "equal";
}

// ─── Shadow Rule Detection ────────────────────────────────────────────

/**
 * Check if statement A shadows statement B.
 * A shadows B if A has higher priority, broader patterns, and same effect.
 */
export function doesStatementShadow(shadow: PolicyStatement, shadowed: PolicyStatement): boolean {
  if (shadow.priority <= shadowed.priority) return false;
  if (!patternContains(shadow.resource, shadowed.resource)) return false;
  if (!patternContains(shadow.action, shadowed.action)) return false;
  if (shadow.effect !== shadowed.effect) return false;

  if (!shadow.conditions || shadow.conditions.length === 0) return true;

  const condRelation = analyzeConditionOverlap(shadowed.conditions, shadow.conditions);
  return condRelation === "a_subset_b" || condRelation === "equal";
}
