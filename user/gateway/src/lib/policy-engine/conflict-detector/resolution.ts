// ─── Zenic-Agents v3 — Conflict Resolution ────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Conflict Resolution
//
// Provides conflict resolution strategies and utilities for resolving
// detected policy conflicts. Complements the ConflictDetector in types.ts.
//
// Design Patterns:
//   - Strategy: pluggable resolution strategies
//   - Command: resolution operations as discrete actions

import type {
  PolicyConflict,
  ConflictResolutionStrategy,
  ConflictResolution,
  ConflictSeverity,
  ConflictType,
  PolicyStatement,
  PolicyEffectV2,
} from "./types";

// ─── Resolution Strategies ────────────────────────────────────────────

/**
 * Apply the deny_wins strategy: if any conflicting statement has a deny effect,
 * the deny effect takes precedence.
 */
export function resolveDenyWins(
  conflict: PolicyConflict,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  const stmtAEffect = conflict.statementA.effect;
  const stmtBEffect = conflict.statementB.effect;

  if (stmtAEffect === "deny" || stmtBEffect === "deny") {
    const winner = stmtAEffect === "deny" ? conflict.statementA : conflict.statementB;
    return {
      winningEffect: "deny",
      winningStatementId: winner.statementId,
      reason: `DENY_WINS: deny effect from statement "${winner.statementId}" in policy "${winner.policyId}" takes precedence`,
    };
  }

  // Neither is deny — conditional wins over allow
  if (stmtAEffect === "conditional" || stmtBEffect === "conditional") {
    const winner = stmtAEffect === "conditional" ? conflict.statementA : conflict.statementB;
    return {
      winningEffect: "conditional",
      winningStatementId: winner.statementId,
      reason: `DENY_WINS (fallback): conditional effect from statement "${winner.statementId}" is more restrictive than allow`,
    };
  }

  // Both allow — first match wins
  return {
    winningEffect: stmtAEffect,
    winningStatementId: conflict.statementA.statementId,
    reason: `DENY_WINS (fallback): both statements allow — first match "${conflict.statementA.statementId}" wins`,
  };
}

/**
 * Apply the priority_wins strategy: the statement with higher priority wins.
 */
export function resolvePriorityWins(
  conflict: PolicyConflict,
  statementA?: PolicyStatement,
  statementB?: PolicyStatement,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  // If we have actual statement objects with priority, compare them
  if (statementA && statementB) {
    if (statementA.priority > statementB.priority) {
      return {
        winningEffect: statementA.effect,
        winningStatementId: statementA.id,
        reason: `PRIORITY_WINS: statement "${statementA.id}" has higher priority (${statementA.priority} vs ${statementB.priority})`,
      };
    } else if (statementB.priority > statementA.priority) {
      return {
        winningEffect: statementB.effect,
        winningStatementId: statementB.id,
        reason: `PRIORITY_WINS: statement "${statementB.id}" has higher priority (${statementB.priority} vs ${statementA.priority})`,
      };
    }
  }

  // Without priority info, fall back to deny_wins
  return resolveDenyWins(conflict);
}

/**
 * Apply the first_match strategy: the first matching statement in evaluation order wins.
 */
export function resolveFirstMatch(
  conflict: PolicyConflict,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  return {
    winningEffect: conflict.statementA.effect,
    winningStatementId: conflict.statementA.statementId,
    reason: `FIRST_MATCH: statement "${conflict.statementA.statementId}" wins as first match in evaluation order`,
  };
}

/**
 * Apply the merge_conditions strategy: both conditions must be satisfied,
 * and the more restrictive effect wins.
 */
export function resolveMergeConditions(
  conflict: PolicyConflict,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  const effectOrder: Record<string, number> = { deny: 0, conditional: 1, allow: 2 };
  const orderA = effectOrder[conflict.statementA.effect] ?? 3;
  const orderB = effectOrder[conflict.statementB.effect] ?? 3;

  if (orderA < orderB) {
    return {
      winningEffect: conflict.statementA.effect,
      winningStatementId: conflict.statementA.statementId,
      reason: `MERGE_CONDITIONS: statement "${conflict.statementA.statementId}" has more restrictive effect (${conflict.statementA.effect})`,
    };
  }

  return {
    winningEffect: conflict.statementB.effect,
    winningStatementId: conflict.statementB.statementId,
    reason: `MERGE_CONDITIONS: statement "${conflict.statementB.statementId}" has more restrictive effect (${conflict.statementB.effect})`,
  };
}

/**
 * Apply the manual strategy: no automatic resolution, requires human review.
 */
export function resolveManual(
  conflict: PolicyConflict,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  return {
    winningEffect: conflict.statementA.effect,
    winningStatementId: conflict.statementA.statementId,
    reason: `MANUAL: conflict requires manual resolution — preserving first statement "${conflict.statementA.statementId}" temporarily`,
  };
}

// ─── Resolution Dispatcher ────────────────────────────────────────────

/**
 * Apply a resolution strategy to a conflict.
 * Returns the resolution outcome with the winning effect and reason.
 */
export function applyResolutionStrategy(
  conflict: PolicyConflict,
  strategy: ConflictResolutionStrategy,
  statementA?: PolicyStatement,
  statementB?: PolicyStatement,
): { winningEffect: PolicyEffectV2; winningStatementId: string; reason: string } {
  switch (strategy) {
    case "deny_wins":
      return resolveDenyWins(conflict);
    case "priority_wins":
      return resolvePriorityWins(conflict, statementA, statementB);
    case "first_match":
      return resolveFirstMatch(conflict);
    case "merge_conditions":
      return resolveMergeConditions(conflict);
    case "manual":
      return resolveManual(conflict);
    default:
      return resolveDenyWins(conflict);
  }
}

// ─── Resolution Validation ────────────────────────────────────────────

/**
 * Validate a conflict resolution.
 * Checks that the resolution strategy is appropriate for the conflict type.
 */
export function validateResolution(
  conflict: PolicyConflict,
  resolution: ConflictResolution,
): { valid: boolean; warnings: string[] } {
  const warnings: string[] = [];

  // Warn if manual resolution is skipped for critical conflicts
  if (conflict.severity === "critical" && resolution.strategy !== "deny_wins" && resolution.strategy !== "manual") {
    warnings.push(
      `Critical conflict resolved with "${resolution.strategy}" instead of "deny_wins" or "manual" — review recommended`,
    );
  }

  // Warn if scope conflicts are auto-resolved
  if (conflict.type === "scope_conflict" && resolution.strategy !== "manual") {
    warnings.push(
      `Scope conflict auto-resolved with "${resolution.strategy}" — manual review recommended for cross-namespace conflicts`,
    );
  }

  // Warn if the resolver is not specified
  if (!resolution.resolvedBy) {
    warnings.push("Resolution has no resolver specified — audit trail may be incomplete");
  }

  return { valid: warnings.length === 0, warnings };
}

// ─── Batch Resolution ─────────────────────────────────────────────────

/**
 * Resolution plan for a batch of conflicts.
 */
export interface BatchResolutionPlan {
  /** Number of conflicts that will be auto-resolved */
  autoResolvable: number;
  /** Number of conflicts that require manual review */
  manualRequired: number;
  /** Recommended default strategy */
  recommendedStrategy: ConflictResolutionStrategy;
  /** Warnings about the batch */
  warnings: string[];
}

/**
 * Analyze a batch of conflicts and create a resolution plan.
 * Determines which conflicts can be auto-resolved and which need manual review.
 */
export function createBatchResolutionPlan(
  conflicts: PolicyConflict[],
): BatchResolutionPlan {
  let autoResolvable = 0;
  let manualRequired = 0;
  const warnings: string[] = [];

  const criticalCount = conflicts.filter((c) => c.severity === "critical").length;
  const scopeCount = conflicts.filter((c) => c.type === "scope_conflict").length;

  for (const conflict of conflicts) {
    if (conflict.resolved) continue;

    if (conflict.type === "scope_conflict") {
      manualRequired++;
    } else if (conflict.severity === "critical" && conflict.type === "effect_contradiction") {
      autoResolvable++; // deny_wins is safe for effect contradictions
    } else {
      autoResolvable++;
    }
  }

  if (criticalCount > 5) {
    warnings.push(`${criticalCount} critical conflicts detected — review recommended before deploying`);
  }

  if (scopeCount > 0) {
    warnings.push(`${scopeCount} scope conflicts require manual resolution`);
  }

  return {
    autoResolvable,
    manualRequired,
    recommendedStrategy: "deny_wins",
    warnings,
  };
}
