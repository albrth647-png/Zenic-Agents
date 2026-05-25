// ─── Zenic-Agents v3 — Impact Reporting ──────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Impact Reporting
//
// Provides reporting utilities for impact analysis results.
// Formats impact analysis results into human-readable reports and summaries.
// Complements the analyzeImpact function in types.ts.

import type {
  ImpactAnalysisResult,
  ImpactCategory,
  BlastRadius,
  DependencyRef,
  DownstreamChange,
  AffectedSetRef,
  AffectedPlaybookRef,
  AffectedToolRef,
  SimulationRiskLevel,
} from "./types";

// ─── Report Formatting ────────────────────────────────────────────────

/**
 * Format an impact analysis result as a multi-line text report.
 */
export function formatImpactReport(result: ImpactAnalysisResult): string {
  const lines: string[] = [];

  lines.push("═".repeat(60));
  lines.push("  IMPACT ANALYSIS REPORT");
  lines.push("═".repeat(60));
  lines.push("");

  // Summary
  lines.push("SUMMARY");
  lines.push("-".repeat(40));
  lines.push(`  Analysis ID:    ${result.analysisId}`);
  lines.push(`  Policy:         ${result.policyId}`);
  lines.push(`  Requested by:   ${result.requestedBy ?? "unknown"}`);
  lines.push(`  Depth:          ${result.depth}`);
  lines.push(`  Duration:       ${result.analysisDuration}ms`);
  lines.push("");

  // Blast Radius
  const br = result.blastRadius;
  lines.push("BLAST RADIUS");
  lines.push("-".repeat(40));
  lines.push(`  Risk Score:           ${br.riskScore}/100`);
  lines.push(`  Risk Level:           ${br.riskLevel.toUpperCase()}`);
  lines.push(`  Affected Resources:   ${br.totalAffectedResources}`);
  lines.push(`  Affected Users:       ${br.totalAffectedUsers}`);
  lines.push(`  Recovery Time:        ~${br.estimatedRecoveryMinutes} minutes`);
  lines.push("");

  // Dependencies
  lines.push("DEPENDENCIES");
  lines.push("-".repeat(40));
  lines.push(`  Direct:    ${result.directDependencies.length}`);
  lines.push(`  Indirect:  ${result.indirectDependencies.length}`);
  lines.push("");

  // Downstream Changes
  if (result.downstreamChanges.length > 0) {
    lines.push("DOWNSTREAM CHANGES");
    lines.push("-".repeat(40));
    for (const change of result.downstreamChanges) {
      lines.push(`  ${change.request}: ${change.currentEffect} → ${change.predictedEffect}`);
      lines.push(`    Confidence: ${(change.confidence * 100).toFixed(0)}%`);
      lines.push(`    Reason: ${change.reason}`);
    }
    lines.push("");
  }

  // Impact Categories
  if (br.categories.length > 0) {
    lines.push("IMPACT CATEGORIES");
    lines.push("-".repeat(40));
    for (const cat of br.categories) {
      lines.push(`  ${cat.name}: ${cat.affectedCount} affected (${cat.severity})`);
      lines.push(`    ${cat.description}`);
    }
    lines.push("");
  }

  lines.push("═".repeat(60));
  return lines.join("\n");
}

/**
 * Format a blast radius as a compact summary string.
 */
export function formatBlastRadiusSummary(br: BlastRadius): string {
  const parts: string[] = [];

  parts.push(`Risk: ${br.riskScore}/100 (${br.riskLevel})`);
  parts.push(`Resources: ${br.totalAffectedResources}`);
  parts.push(`Users: ${br.totalAffectedUsers}`);
  parts.push(`Recovery: ~${br.estimatedRecoveryMinutes}min`);

  return parts.join(" | ");
}

/**
 * Format a list of downstream changes as a summary table.
 */
export function formatDownstreamChangesTable(changes: DownstreamChange[]): string {
  if (changes.length === 0) {
    return "No downstream changes detected.";
  }

  const lines: string[] = [];
  lines.push("Request                         | Before    | After     | Confidence");
  lines.push("-".repeat(70));

  for (const change of changes) {
    const request = change.request.padEnd(30);
    const before = change.currentEffect.padEnd(9);
    const after = change.predictedEffect.padEnd(9);
    const confidence = `${(change.confidence * 100).toFixed(0)}%`;
    lines.push(`${request} | ${before} | ${after} | ${confidence}`);
  }

  return lines.join("\n");
}

// ─── Impact Category Formatting ───────────────────────────────────────

/**
 * Format impact categories as a bullet-point list.
 */
export function formatImpactCategories(categories: ImpactCategory[]): string {
  if (categories.length === 0) {
    return "No impact categories identified.";
  }

  const lines: string[] = [];
  for (const cat of categories) {
    const severityBadge =
      cat.severity === "critical" ? "🔴" :
      cat.severity === "high" ? "🟠" :
      cat.severity === "medium" ? "🟡" :
      "🟢";
    lines.push(`  ${severityBadge} ${cat.name}: ${cat.affectedCount} (${cat.severity})`);
    lines.push(`     ${cat.description}`);
  }

  return lines.join("\n");
}

// ─── Risk Assessment ──────────────────────────────────────────────────

/**
 * Assess overall risk from an impact analysis result.
 * Returns a human-readable risk assessment.
 */
export function assessRisk(result: ImpactAnalysisResult): {
  level: SimulationRiskLevel;
  score: number;
  assessment: string;
  recommendations: string[];
} {
  const { blastRadius, downstreamChanges } = result;
  const recommendations: string[] = [];

  const allowToDeny = downstreamChanges.filter(
    (c) => c.currentEffect === "allow" && c.predictedEffect === "deny",
  ).length;
  const denyToAllow = downstreamChanges.filter(
    (c) => c.currentEffect === "deny" && c.predictedEffect === "allow",
  ).length;

  if (allowToDeny > 0) {
    recommendations.push(
      `Review ${allowToDeny} new denial(s) — affected workflows may break`,
    );
  }

  if (denyToAllow > 0) {
    recommendations.push(
      `Review ${denyToAllow} new allowance(s) — security posture may be weakened`,
    );
  }

  if (blastRadius.totalAffectedUsers > 50) {
    recommendations.push(
      `High user impact (${blastRadius.totalAffectedUsers} users) — consider staged rollout`,
    );
  }

  if (blastRadius.categories.some((c) => c.severity === "critical")) {
    recommendations.push(
      "Critical impact categories detected — require approval before deployment",
    );
  }

  if (blastRadius.estimatedRecoveryMinutes > 60) {
    recommendations.push(
      `Long recovery time (~${blastRadius.estimatedRecoveryMinutes} min) — prepare rollback plan`,
    );
  }

  const assessment =
    blastRadius.riskLevel === "critical"
      ? "CRITICAL: This change poses significant risk and requires thorough review"
      : blastRadius.riskLevel === "high"
        ? "HIGH: This change has notable impact — review recommended before proceeding"
        : blastRadius.riskLevel === "medium"
          ? "MEDIUM: Moderate impact expected — standard review process sufficient"
          : "LOW: Minimal impact expected — safe to proceed with normal monitoring";

  return {
    level: blastRadius.riskLevel,
    score: blastRadius.riskScore,
    assessment,
    recommendations,
  };
}

// ─── Dependency Formatting ────────────────────────────────────────────

/**
 * Format dependency lists as a summary.
 */
export function formatDependencySummary(
  directDeps: DependencyRef[],
  indirectDeps: DependencyRef[],
): string {
  const lines: string[] = [];

  if (directDeps.length > 0) {
    lines.push(`Direct Dependencies (${directDeps.length}):`);
    for (const dep of directDeps) {
      const hardTag = dep.hardDependency ? "[HARD]" : "[SOFT]";
      lines.push(`  ${hardTag} ${dep.type}: ${dep.name} (${dep.id})`);
    }
  } else {
    lines.push("No direct dependencies found.");
  }

  if (indirectDeps.length > 0) {
    lines.push("");
    lines.push(`Indirect Dependencies (${indirectDeps.length}):`);
    for (const dep of indirectDeps) {
      lines.push(`  ${dep.type}: ${dep.name} (${dep.id})`);
    }
  }

  return lines.join("\n");
}

// ─── Quick Summary ────────────────────────────────────────────────────

/**
 * Generate a one-line impact summary.
 */
export function quickImpactSummary(result: ImpactAnalysisResult): string {
  const br = result.blastRadius;
  return (
    `Impact: ${br.riskScore}/100 (${br.riskLevel}) | ` +
    `${br.totalAffectedResources} resources | ` +
    `${br.totalAffectedUsers} users | ` +
    `${result.downstreamChanges.length} changes`
  );
}
