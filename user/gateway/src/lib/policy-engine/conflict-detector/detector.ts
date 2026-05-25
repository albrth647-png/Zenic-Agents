// ─── Zenic-Agents v3 — Conflict Detector ─────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Conflict Detection
//
// Re-exports the ConflictDetector class from types.ts and provides
// additional convenience wrappers for conflict detection operations.

export {
  ConflictDetector,
  type ConflictDetectionOptions,
} from "./types";

import { db } from "@/lib/db";
import type {
  PolicyConflict,
  ConflictReport,
  ConflictResolutionStrategy,
  ConflictSeverity,
  ConflictType,
} from "./types";

// ─── Severity Scoring ─────────────────────────────────────────────────

const SEVERITY_WEIGHTS: Record<string, number> = {
  critical: 25,
  high: 15,
  medium: 8,
  low: 3,
  info: 1,
};

/**
 * Compute a conflict score (0-100) from a list of conflicts.
 * Unresolved conflicts count fully; resolved ones count 20%.
 */
export function computeConflictScore(conflicts: PolicyConflict[]): number {
  let score = 0;
  for (const c of conflicts) {
    const weight = c.resolved
      ? (SEVERITY_WEIGHTS[c.severity] ?? 1) * 0.2
      : (SEVERITY_WEIGHTS[c.severity] ?? 1);
    score += weight;
  }
  return Math.min(100, Math.round(score));
}

// ─── Severity Helpers ─────────────────────────────────────────────────

/**
 * Get an empty by-severity map initialized to zero for all severity levels.
 */
export function emptyBySeverity(): Record<string, number> {
  return {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };
}

/**
 * Get an empty by-type map initialized to zero for all conflict types.
 */
export function emptyByType(): Record<string, number> {
  return {
    effect_contradiction: 0,
    priority_collision: 0,
    condition_overlap: 0,
    redundant_rule: 0,
    shadow_rule: 0,
    scope_conflict: 0,
  };
}

/**
 * Compute by-severity and by-type counts from a list of conflicts.
 */
export function computeConflictCounts(conflicts: PolicyConflict[]): {
  bySeverity: Record<string, number>;
  byType: Record<string, number>;
} {
  const bySeverity = emptyBySeverity();
  const byType = emptyByType();

  for (const c of conflicts) {
    bySeverity[c.severity] = (bySeverity[c.severity] ?? 0) + 1;
    byType[c.type] = (byType[c.type] ?? 0) + 1;
  }

  return { bySeverity, byType };
}

// ─── Summary Formatting ───────────────────────────────────────────────

/**
 * Format a conflict report summary string.
 */
export function formatConflictSummary(
  totalConflicts: number,
  conflictScore: number,
  totalPolicies: number,
): string {
  if (totalConflicts === 0) {
    return `No conflicts detected across ${totalPolicies} active policy/policies. Conflict score: 0/100.`;
  }

  const riskLabel =
    conflictScore <= 20 ? "LOW" :
    conflictScore <= 50 ? "MEDIUM" :
    conflictScore <= 80 ? "HIGH" :
    "CRITICAL";

  return (
    `${totalConflicts} conflict(s) detected across ${totalPolicies} active policy/policies. ` +
    `Conflict score: ${conflictScore}/100 (${riskLabel} risk).`
  );
}

// ─── Resolution Strategy Helpers ──────────────────────────────────────

/**
 * Suggest a resolution strategy based on conflict type.
 */
export function suggestResolutionStrategy(type: ConflictType): ConflictResolutionStrategy {
  switch (type) {
    case "effect_contradiction":
      return "deny_wins";
    case "priority_collision":
      return "priority_wins";
    case "condition_overlap":
      return "merge_conditions";
    case "redundant_rule":
    case "shadow_rule":
      return "first_match";
    case "scope_conflict":
      return "manual";
    default:
      return "manual";
  }
}

/**
 * Determine severity based on conflict type and effects involved.
 */
export function determineSeverity(
  type: ConflictType,
  effectA: string,
  effectB: string,
): ConflictSeverity {
  switch (type) {
    case "effect_contradiction":
      if (
        (effectA === "allow" && effectB === "deny") ||
        (effectA === "deny" && effectB === "allow")
      ) {
        return "critical";
      }
      return "high";
    case "priority_collision":
    case "scope_conflict":
      return "high";
    case "condition_overlap":
      return "medium";
    case "redundant_rule":
      return "low";
    case "shadow_rule":
      return "info";
    default:
      return "medium";
  }
}

// ─── Conflict Description Generation ──────────────────────────────────

/**
 * Generate a human-readable description for a conflict.
 */
export function generateConflictDescription(
  type: ConflictType,
  refA: { statementId: string; policyId: string; effect: string; resource: string; action: string },
  refB: { statementId: string; policyId: string; effect: string; resource: string; action: string },
): string {
  switch (type) {
    case "effect_contradiction":
      return (
        `Effect contradiction: "${refA.statementId}" in policy "${refA.policyId}" (${refA.effect}) ` +
        `conflicts with "${refB.statementId}" in policy "${refB.policyId}" (${refB.effect}) ` +
        `on resource "${refA.resource}" action "${refA.action}"`
      );
    case "priority_collision":
      return (
        `Priority collision: "${refA.statementId}" in policy "${refA.policyId}" and ` +
        `"${refB.statementId}" in policy "${refB.policyId}" have overlapping scope ` +
        `with same priority level but different effects`
      );
    case "condition_overlap":
      return (
        `Condition overlap: "${refA.statementId}" in policy "${refA.policyId}" and ` +
        `"${refB.statementId}" in policy "${refB.policyId}" have overlapping condition scopes ` +
        `on resource "${refA.resource}" action "${refA.action}"`
      );
    case "redundant_rule":
      return (
        `Redundant rule: "${refB.statementId}" in policy "${refB.policyId}" ` +
        `is a subset of "${refA.statementId}" in policy "${refA.policyId}" ` +
        `and does not change the evaluation outcome`
      );
    case "shadow_rule":
      return (
        `Shadow rule: "${refB.statementId}" in policy "${refB.policyId}" ` +
        `is never reached because "${refA.statementId}" in policy "${refA.policyId}" ` +
        `always matches first with the same effect (higher priority)`
      );
    case "scope_conflict":
      return (
        `Scope conflict: "${refA.statementId}" in policy "${refA.policyId}" ` +
        `and "${refB.statementId}" in policy "${refB.policyId}" ` +
        `from different namespaces have overlapping scope`
      );
    default:
      return `Unknown conflict between "${refA.statementId}" and "${refB.statementId}"`;
  }
}
