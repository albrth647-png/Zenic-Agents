// ─── Zenic-Agents v3 — Policy Composition Merger ──────────────────────
// Phase 4: Declarative Versioned Policy Engine — Merge Strategies
//
// Provides pure merge-strategy functions that operate on arrays of
// PolicyStatement[][]. These are the building blocks used by
// CompositionEngine inside types.ts.
//
// Design Patterns:
//   - Strategy: each merge function is a pluggable algorithm
//   - Fingerprinting: deterministic SHA-256 deduplication of statements

import { createHash } from "crypto";
import type {
  PolicyStatement,
  PolicyEffectV2,
  PolicyConflict,
  ConflictType,
  ConflictSeverity,
  ConflictResolutionStrategy,
  ConflictStatementRef,
  CompositionStats,
  MergeStrategy,
} from "./types";

// ─── Constants ────────────────────────────────────────────────────────

const EFFECT_ORDER: Record<string, number> = { deny: 0, conditional: 1, allow: 2 };

const VALID_MERGE_STRATEGIES: ReadonlySet<string> = new Set([
  "union",
  "intersection",
  "override",
  "extend",
  "priority_merge",
]);

// ─── Statement Fingerprinting ─────────────────────────────────────────

/**
 * Create a deterministic fingerprint for a statement for deduplication.
 * Two statements are considered "exact duplicates" if they share the same
 * id, effect, resource, action, and conditions.
 */
export function statementFingerprint(stmt: PolicyStatement): string {
  const core = {
    id: stmt.id,
    effect: stmt.effect,
    resource: stmt.resource,
    action: stmt.action,
    conditions: stmt.conditions ?? [],
  };
  return createHash("sha256")
    .update(JSON.stringify(core))
    .digest("hex");
}

/**
 * Create a resource+action key for intersection matching.
 */
export function resourceActionKey(stmt: PolicyStatement): string {
  return `${stmt.resource}::${stmt.action}`;
}

/**
 * Validate that a merge strategy string is recognized.
 */
export function isValidMergeStrategy(strategy: string): strategy is MergeStrategy {
  return VALID_MERGE_STRATEGIES.has(strategy);
}

// ─── Merge Strategy: UNION ────────────────────────────────────────────

/**
 * UNION merge: Collect all statements from all policies,
 * remove exact duplicates (same id, effect, resource, action, conditions),
 * sort by priority (highest first).
 */
export function mergeUnion(
  policyStatements: PolicyStatement[][],
): { statements: PolicyStatement[]; stats: Pick<CompositionStats, "unionCount" | "duplicatesRemoved"> } {
  const seen = new Map<string, PolicyStatement>();
  let duplicatesRemoved = 0;

  for (const stmts of policyStatements) {
    for (const stmt of stmts) {
      const fp = statementFingerprint(stmt);
      if (seen.has(fp)) {
        duplicatesRemoved++;
      } else {
        seen.set(fp, stmt);
      }
    }
  }

  const statements = [...seen.values()].sort((a, b) => b.priority - a.priority);

  return {
    statements,
    stats: {
      unionCount: statements.length,
      duplicatesRemoved,
    },
  };
}

// ─── Merge Strategy: INTERSECTION ─────────────────────────────────────

/**
 * INTERSECTION merge: Only include statements where the same resource+action
 * pair exists in ALL policies. If different effects for same pair, deny wins.
 */
export function mergeIntersection(
  policyStatements: PolicyStatement[][],
): { statements: PolicyStatement[]; stats: Pick<CompositionStats, "intersectionCount" | "duplicatesRemoved">; conflicts: PolicyConflict[] } {
  if (policyStatements.length === 0) {
    return { statements: [], stats: { intersectionCount: 0, duplicatesRemoved: 0 }, conflicts: [] };
  }

  if (policyStatements.length === 1) {
    return {
      statements: policyStatements[0]!.sort((a, b) => b.priority - a.priority),
      stats: { intersectionCount: policyStatements[0]!.length, duplicatesRemoved: 0 },
      conflicts: [],
    };
  }

  const conflicts: PolicyConflict[] = [];
  const policyCount = policyStatements.length;

  const raMap = new Map<string, PolicyStatement[]>();
  for (const stmts of policyStatements) {
    for (const stmt of stmts) {
      const key = resourceActionKey(stmt);
      if (!raMap.has(key)) {
        raMap.set(key, []);
      }
      raMap.get(key)!.push(stmt);
    }
  }

  const result: PolicyStatement[] = [];
  let duplicatesRemoved = 0;

  for (const [key, stmts] of raMap.entries()) {
    let policyCoverage = 0;
    for (const policyStmts of policyStatements) {
      if (policyStmts.some((s) => resourceActionKey(s) === key)) {
        policyCoverage++;
      }
    }

    if (policyCoverage < policyCount) {
      duplicatesRemoved += stmts.length;
      continue;
    }

    const uniqueEffects = new Set(stmts.map((s) => s.effect));
    if (uniqueEffects.size === 1) {
      const best = stmts.sort((a, b) => b.priority - a.priority)[0]!;
      result.push(best);
      duplicatesRemoved += stmts.length - 1;
    } else {
      const denyStmt = stmts.find((s) => s.effect === "deny");
      const best = denyStmt ?? stmts.sort((a, b) => b.priority - a.priority)[0]!;

      const effectGroups = new Map<string, PolicyStatement[]>();
      for (const s of stmts) {
        if (!effectGroups.has(s.effect)) effectGroups.set(s.effect, []);
        effectGroups.get(s.effect)!.push(s);
      }

      const effectEntries = [...effectGroups.entries()];
      if (effectEntries.length >= 2) {
        const groupA = effectEntries[0]!;
        const groupB = effectEntries[1]!;
        conflicts.push({
          id: `conflict_intersection_${key.replace(/[^a-zA-Z0-9]/g, "_")}`,
          type: "effect_contradiction" as ConflictType,
          severity: "critical" as ConflictSeverity,
          statementA: {
            policyId: "composed",
            version: "1.0.0",
            statementId: groupA[1][0]!.id,
            effect: groupA[1][0]!.effect,
            resource: groupA[1][0]!.resource,
            action: groupA[1][0]!.action,
          } as ConflictStatementRef,
          statementB: {
            policyId: "composed",
            version: "1.0.0",
            statementId: groupB[1][0]!.id,
            effect: groupB[1][0]!.effect,
            resource: groupB[1][0]!.resource,
            action: groupB[1][0]!.action,
          } as ConflictStatementRef,
          description: `INTERSECTION: resource+action "${key}" has conflicting effects (${[...uniqueEffects].join(", ")}), deny wins`,
          suggestedResolution: "deny_wins" as ConflictResolutionStrategy,
          resolved: true,
        });
      }

      result.push(best);
      duplicatesRemoved += stmts.length - 1;
    }
  }

  result.sort((a, b) => b.priority - a.priority);

  return {
    statements: result,
    stats: {
      intersectionCount: result.length,
      duplicatesRemoved,
    },
    conflicts,
  };
}

// ─── Merge Strategy: OVERRIDE ─────────────────────────────────────────

/**
 * OVERRIDE merge: Process policies in set entry order.
 * If a statement with the same ID exists in a later policy, replace it.
 * New statements from later policies are added.
 */
export function mergeOverride(
  policyStatements: PolicyStatement[][],
): { statements: PolicyStatement[]; stats: Pick<CompositionStats, "overrideCount" | "duplicatesRemoved"> } {
  const statementMap = new Map<string, PolicyStatement>();
  let overrideCount = 0;
  let duplicatesRemoved = 0;

  for (const stmts of policyStatements) {
    for (const stmt of stmts) {
      if (statementMap.has(stmt.id)) {
        statementMap.set(stmt.id, stmt);
        overrideCount++;
        duplicatesRemoved++;
      } else {
        statementMap.set(stmt.id, stmt);
      }
    }
  }

  const statements = [...statementMap.values()].sort((a, b) => b.priority - a.priority);

  return {
    statements,
    stats: {
      overrideCount,
      duplicatesRemoved,
    },
  };
}

// ─── Merge Strategy: EXTEND ───────────────────────────────────────────

/**
 * EXTEND merge: Start with the first policy.
 * Add statements from subsequent policies only if they don't conflict.
 * Never remove existing statements.
 * A conflict = same resource+action with different effect.
 */
export function mergeExtend(
  policyStatements: PolicyStatement[][],
): { statements: PolicyStatement[]; stats: Pick<CompositionStats, "duplicatesRemoved">; conflicts: PolicyConflict[] } {
  if (policyStatements.length === 0) {
    return { statements: [], stats: { duplicatesRemoved: 0 }, conflicts: [] };
  }

  const conflicts: PolicyConflict[] = [];
  const result: PolicyStatement[] = [...policyStatements[0]!];
  let duplicatesRemoved = 0;

  const existingRA = new Map<string, PolicyStatement>();
  const existingIds = new Set<string>();
  for (const stmt of result) {
    existingRA.set(resourceActionKey(stmt), stmt);
    existingIds.add(stmt.id);
  }

  for (let pi = 1; pi < policyStatements.length; pi++) {
    const stmts = policyStatements[pi]!;
    for (const stmt of stmts) {
      const raKey = resourceActionKey(stmt);

      if (existingIds.has(stmt.id)) {
        duplicatesRemoved++;
        continue;
      }

      const existing = existingRA.get(raKey);
      if (existing && existing.effect !== stmt.effect) {
        duplicatesRemoved++;
        conflicts.push({
          id: `conflict_extend_${raKey.replace(/[^a-zA-Z0-9]/g, "_")}_p${pi}`,
          type: "effect_contradiction" as ConflictType,
          severity: "high" as ConflictSeverity,
          statementA: {
            policyId: "composed",
            version: "1.0.0",
            statementId: existing.id,
            effect: existing.effect,
            resource: existing.resource,
            action: existing.action,
          } as ConflictStatementRef,
          statementB: {
            policyId: "composed",
            version: "1.0.0",
            statementId: stmt.id,
            effect: stmt.effect,
            resource: stmt.resource,
            action: stmt.action,
          } as ConflictStatementRef,
          description: `EXTEND: resource+action "${raKey}" conflict — existing "${existing.effect}" blocks new "${stmt.effect}" from statement "${stmt.id}"`,
          suggestedResolution: "first_match" as ConflictResolutionStrategy,
          resolved: true,
        });
        continue;
      }

      result.push(stmt);
      existingRA.set(raKey, stmt);
      existingIds.add(stmt.id);
    }
  }

  result.sort((a, b) => b.priority - a.priority);

  return {
    statements: result,
    stats: { duplicatesRemoved },
    conflicts,
  };
}

// ─── Merge Strategy: PRIORITY_MERGE ───────────────────────────────────

/**
 * PRIORITY_MERGE merge: Collect all statements, sort by priority (highest first).
 * On same priority with different effects: deny wins.
 * Build a merged document with the result.
 */
export function mergePriorityMerge(
  policyStatements: PolicyStatement[][],
): { statements: PolicyStatement[]; stats: Pick<CompositionStats, "duplicatesRemoved">; conflicts: PolicyConflict[] } {
  const allStatements: PolicyStatement[] = [];
  for (const stmts of policyStatements) {
    allStatements.push(...stmts);
  }

  allStatements.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    return (EFFECT_ORDER[a.effect] ?? 3) - (EFFECT_ORDER[b.effect] ?? 3);
  });

  const conflicts: PolicyConflict[] = [];
  const priorityRAMap = new Map<string, PolicyStatement[]>();

  for (const stmt of allStatements) {
    const key = `${stmt.priority}::${resourceActionKey(stmt)}`;
    if (!priorityRAMap.has(key)) {
      priorityRAMap.set(key, []);
    }
    priorityRAMap.get(key)!.push(stmt);
  }

  for (const [key, stmts] of priorityRAMap.entries()) {
    if (stmts.length > 1) {
      const uniqueEffects = new Set(stmts.map((s) => s.effect));
      if (uniqueEffects.size > 1) {
        const [prioStr, ...raParts] = key.split("::");
        const raKey = raParts.join("::");
        const groupA = stmts[0]!;
        const groupB = stmts[1]!;
        conflicts.push({
          id: `conflict_pmerge_${prioStr}_${raKey.replace(/[^a-zA-Z0-9]/g, "_")}`,
          type: "priority_collision" as ConflictType,
          severity: "high" as ConflictSeverity,
          statementA: {
            policyId: "composed",
            version: "1.0.0",
            statementId: groupA.id,
            effect: groupA.effect,
            resource: groupA.resource,
            action: groupA.action,
          } as ConflictStatementRef,
          statementB: {
            policyId: "composed",
            version: "1.0.0",
            statementId: groupB.id,
            effect: groupB.effect,
            resource: groupB.resource,
            action: groupB.action,
          } as ConflictStatementRef,
          description: `PRIORITY_MERGE: priority ${prioStr} resource+action "${raKey}" has conflicting effects (${[...uniqueEffects].join(", ")}), deny wins`,
          suggestedResolution: "deny_wins" as ConflictResolutionStrategy,
          resolved: true,
        });
      }
    }
  }

  const seen = new Map<string, PolicyStatement>();
  let duplicatesRemoved = 0;
  for (const stmt of allStatements) {
    if (seen.has(stmt.id)) {
      duplicatesRemoved++;
    } else {
      seen.set(stmt.id, stmt);
    }
  }

  const statements = [...seen.values()];

  return {
    statements,
    stats: { duplicatesRemoved },
    conflicts,
  };
}

// ─── Merge Dispatcher ─────────────────────────────────────────────────

/**
 * Apply a named merge strategy to the given policy statement arrays.
 * Returns the merged statements, stats, and any detected conflicts.
 */
export function applyMergeStrategy(
  strategy: MergeStrategy,
  policyStatements: PolicyStatement[][],
): {
  statements: PolicyStatement[];
  stats: Partial<CompositionStats>;
  conflicts: PolicyConflict[];
} {
  switch (strategy) {
    case "union": {
      const result = mergeUnion(policyStatements);
      return { statements: result.statements, stats: result.stats, conflicts: [] };
    }
    case "intersection": {
      const result = mergeIntersection(policyStatements);
      return { statements: result.statements, stats: result.stats, conflicts: result.conflicts };
    }
    case "override": {
      const result = mergeOverride(policyStatements);
      return { statements: result.statements, stats: result.stats, conflicts: [] };
    }
    case "extend": {
      const result = mergeExtend(policyStatements);
      return { statements: result.statements, stats: result.stats, conflicts: result.conflicts };
    }
    case "priority_merge": {
      const result = mergePriorityMerge(policyStatements);
      return { statements: result.statements, stats: result.stats, conflicts: result.conflicts };
    }
    default:
      throw new Error(`Unknown merge strategy: ${strategy}`);
  }
}

// ─── Statement Counting Utility ───────────────────────────────────────

/**
 * Count statements by effect type.
 */
export function countByEffect(
  statements: PolicyStatement[],
): Record<PolicyEffectV2, number> {
  const byEffect: Record<PolicyEffectV2, number> = {
    allow: 0,
    deny: 0,
    conditional: 0,
  };
  for (const stmt of statements) {
    byEffect[stmt.effect] = (byEffect[stmt.effect] ?? 0) + 1;
  }
  return byEffect;
}
