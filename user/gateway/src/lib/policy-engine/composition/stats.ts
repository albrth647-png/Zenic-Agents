// ─── Zenic-Agents v3 — Policy Composition Statistics ─────────────────
// Phase 4: Declarative Versioned Policy Engine — Composition Statistics
//
// Provides utilities for computing and formatting composition statistics
// from merged policy documents. Complements the CompositionEngine in types.ts.

import type {
  PolicyStatement,
  PolicyEffectV2,
  CompositionStats,
  ComposedPolicyResult,
  PolicyConflict,
  ConflictSeverity,
  ConflictType,
} from "./types";

// ─── Stats Aggregation ────────────────────────────────────────────────

/**
 * Aggregate composition stats from a ComposedPolicyResult.
 * Returns a formatted summary object.
 */
export function aggregateStats(result: ComposedPolicyResult): CompositionSummary {
  const { stats, totalStatements, byEffect, conflicts } = result;

  const resolvedConflicts = conflicts.filter((c) => c.resolved).length;
  const unresolvedConflicts = conflicts.filter((c) => !c.resolved).length;

  return {
    totalStatements,
    byEffect: { ...byEffect },
    duplicatesRemoved: stats.duplicatesRemoved,
    unionCount: stats.unionCount,
    intersectionCount: stats.intersectionCount,
    overrideCount: stats.overrideCount,
    mergeDurationMs: stats.mergeDuration,
    totalConflicts: conflicts.length,
    resolvedConflicts,
    unresolvedConflicts,
    conflictRate: totalStatements > 0 ? conflicts.length / totalStatements : 0,
  };
}

/**
 * Summary of a composition operation.
 */
export interface CompositionSummary {
  totalStatements: number;
  byEffect: Record<PolicyEffectV2, number>;
  duplicatesRemoved: number;
  unionCount: number;
  intersectionCount: number;
  overrideCount: number;
  mergeDurationMs: number;
  totalConflicts: number;
  resolvedConflicts: number;
  unresolvedConflicts: number;
  conflictRate: number;
}

// ─── Stats Formatting ─────────────────────────────────────────────────

/**
 * Format composition stats as a human-readable string.
 */
export function formatStats(stats: CompositionStats): string {
  const parts: string[] = [];

  if (stats.unionCount > 0) {
    parts.push(`union: ${stats.unionCount} statements`);
  }
  if (stats.intersectionCount > 0) {
    parts.push(`intersection: ${stats.intersectionCount} statements`);
  }
  if (stats.overrideCount > 0) {
    parts.push(`override: ${stats.overrideCount} replacements`);
  }
  if (stats.duplicatesRemoved > 0) {
    parts.push(`${stats.duplicatesRemoved} duplicates removed`);
  }
  parts.push(`completed in ${stats.mergeDuration}ms`);

  return parts.join(", ");
}

/**
 * Format a CompositionSummary as a multi-line report.
 */
export function formatSummaryReport(summary: CompositionSummary): string {
  const lines: string[] = [];

  lines.push(`Composition Summary:`);
  lines.push(`  Total statements: ${summary.totalStatements}`);
  lines.push(`  By effect: allow=${summary.byEffect.allow}, deny=${summary.byEffect.deny}, conditional=${summary.byEffect.conditional}`);
  lines.push(`  Duplicates removed: ${summary.duplicatesRemoved}`);
  lines.push(`  Merge duration: ${summary.mergeDurationMs}ms`);
  lines.push(`  Conflicts: ${summary.totalConflicts} (${summary.resolvedConflicts} resolved, ${summary.unresolvedConflicts} unresolved)`);
  lines.push(`  Conflict rate: ${(summary.conflictRate * 100).toFixed(1)}%`);

  return lines.join("\n");
}

// ─── Effect Distribution ──────────────────────────────────────────────

/**
 * Compute the effect distribution as percentages.
 */
export function effectDistribution(
  byEffect: Record<PolicyEffectV2, number>,
): Record<PolicyEffectV2, number> {
  const total = byEffect.allow + byEffect.deny + byEffect.conditional;
  if (total === 0) {
    return { allow: 0, deny: 0, conditional: 0 };
  }
  return {
    allow: Math.round((byEffect.allow / total) * 100),
    deny: Math.round((byEffect.deny / total) * 100),
    conditional: Math.round((byEffect.conditional / total) * 100),
  };
}

// ─── Conflict Statistics ──────────────────────────────────────────────

/**
 * Compute conflict statistics grouped by severity and type.
 */
export function conflictStats(
  conflicts: PolicyConflict[],
): {
  bySeverity: Record<string, number>;
  byType: Record<string, number>;
  resolvedCount: number;
  unresolvedCount: number;
} {
  const bySeverity: Record<string, number> = {};
  const byType: Record<string, number> = {};
  let resolvedCount = 0;
  let unresolvedCount = 0;

  for (const conflict of conflicts) {
    bySeverity[conflict.severity] = (bySeverity[conflict.severity] ?? 0) + 1;
    byType[conflict.type] = (byType[conflict.type] ?? 0) + 1;
    if (conflict.resolved) {
      resolvedCount++;
    } else {
      unresolvedCount++;
    }
  }

  return { bySeverity, byType, resolvedCount, unresolvedCount };
}

// ─── Composition Health Score ─────────────────────────────────────────

/**
 * Compute a health score (0-100) for a composition result.
 * Higher is better. Factors: few conflicts, no critical severity,
 * fast merge time, minimal duplicates.
 */
export function compositionHealthScore(result: ComposedPolicyResult): number {
  let score = 100;

  // Deduct for unresolved conflicts
  const unresolvedCritical = result.conflicts.filter(
    (c) => !c.resolved && c.severity === "critical",
  ).length;
  const unresolvedHigh = result.conflicts.filter(
    (c) => !c.resolved && c.severity === "high",
  ).length;
  const unresolvedOther = result.conflicts.filter(
    (c) => !c.resolved && c.severity !== "critical" && c.severity !== "high",
  ).length;

  score -= unresolvedCritical * 20;
  score -= unresolvedHigh * 10;
  score -= unresolvedOther * 3;

  // Deduct for high duplicate ratio
  if (result.totalStatements > 0) {
    const duplicateRatio = result.stats.duplicatesRemoved / (result.totalStatements + result.stats.duplicatesRemoved);
    if (duplicateRatio > 0.5) {
      score -= 10;
    } else if (duplicateRatio > 0.3) {
      score -= 5;
    }
  }

  // Deduct for slow merge
  if (result.stats.mergeDuration > 5000) {
    score -= 10;
  } else if (result.stats.mergeDuration > 2000) {
    score -= 5;
  }

  return Math.max(0, Math.min(100, score));
}
