// ─── Zenic-Agents v3 — Simulation Reporting ──────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Simulation Reporting
//
// Provides reporting utilities for simulation results.
// Formats simulation results into human-readable reports and summaries.
// Complements the runSimulation function in types.ts.

import type {
  SimulationResult,
  VerdictChange,
  VerdictChangeCategory,
  PolicyConflict,
  SimulationRisk,
  ComplianceImpact,
  SimulationRiskLevel,
} from "./types";

// ─── Report Formatting ────────────────────────────────────────────────

/**
 * Format a simulation result as a comprehensive multi-line text report.
 */
export function formatSimulationReport(result: SimulationResult): string {
  const lines: string[] = [];

  lines.push("═".repeat(60));
  lines.push("  SIMULATION REPORT");
  lines.push("═".repeat(60));
  lines.push("");

  // Summary
  lines.push("SUMMARY");
  lines.push("-".repeat(40));
  lines.push(`  Simulation ID:  ${result.id}`);
  lines.push(`  Name:           ${result.name}`);
  lines.push(`  Test Requests:  ${result.totalRequests}`);
  lines.push(`  Verdict Changes: ${result.verdictChanges.length}`);
  lines.push(`  Unchanged:       ${result.unchangedCount}`);
  lines.push("");

  // Risk
  lines.push("RISK ASSESSMENT");
  lines.push("-".repeat(40));
  lines.push(`  Impact Score:  ${result.impactScore}/100`);
  lines.push(`  Risk Level:    ${result.risk.level.toUpperCase()}`);
  if (result.risk.factors.length > 0) {
    lines.push("  Risk Factors:");
    for (const factor of result.risk.factors) {
      lines.push(`    - ${factor}`);
    }
  }
  lines.push(`  New Denials:    ${result.risk.newDenialsCount}`);
  lines.push(`  New Allowances: ${result.risk.newAllowancesCount}`);
  lines.push("");

  // Verdict Changes
  if (result.verdictChanges.length > 0) {
    lines.push("VERDICT CHANGES");
    lines.push("-".repeat(40));
    for (const vc of result.verdictChanges) {
      lines.push(`  ${vc.request}: ${vc.beforeEffect} → ${vc.afterEffect} (${vc.category})`);
      lines.push(`    ${vc.description}`);
    }
    lines.push("");
  }

  // Conflicts
  if (result.newConflicts.length > 0 || result.resolvedConflicts.length > 0) {
    lines.push("CONFLICTS");
    lines.push("-".repeat(40));
    if (result.newConflicts.length > 0) {
      lines.push(`  New conflicts: ${result.newConflicts.length}`);
      for (const c of result.newConflicts.slice(0, 10)) {
        lines.push(`    - [${c.severity}] ${c.description}`);
      }
    }
    if (result.resolvedConflicts.length > 0) {
      lines.push(`  Resolved conflicts: ${result.resolvedConflicts.length}`);
    }
    lines.push("");
  }

  // Compliance
  if (result.complianceImpact) {
    lines.push("COMPLIANCE IMPACT");
    lines.push("-".repeat(40));
    const ci = result.complianceImpact;
    if (ci.affectedStandards.length > 0) {
      lines.push(`  Affected Standards: ${ci.affectedStandards.join(", ")}`);
    }
    if (ci.newGaps.length > 0) {
      lines.push("  New Gaps:");
      for (const gap of ci.newGaps) {
        lines.push(`    - ${gap}`);
      }
    }
    lines.push(`  Score Change: ${ci.scoreChange >= 0 ? "+" : ""}${ci.scoreChange}`);
    lines.push("");
  }

  lines.push("═".repeat(60));
  return lines.join("\n");
}

// ─── Summary Formatting ───────────────────────────────────────────────

/**
 * Generate a human-readable summary for a simulation result.
 */
export function generateSummary(
  totalRequests: number,
  verdictChanges: VerdictChange[],
  impactScore: number,
  riskLevel: SimulationRiskLevel,
  newConflicts: PolicyConflict[],
  resolvedConflicts: PolicyConflict[],
): string {
  const lines: string[] = [];

  lines.push(`Simulation analyzed ${totalRequests} test request(s).`);

  if (verdictChanges.length === 0) {
    lines.push("No verdict changes detected — proposed changes have no impact on current evaluations.");
  } else {
    const byCategory = new Map<VerdictChangeCategory, number>();
    for (const vc of verdictChanges) {
      byCategory.set(vc.category, (byCategory.get(vc.category) ?? 0) + 1);
    }

    lines.push(`${verdictChanges.length} verdict change(s) detected:`);
    for (const [category, count] of byCategory) {
      lines.push(`  - ${category}: ${count}`);
    }
  }

  lines.push(`Impact score: ${impactScore}/100 (${riskLevel} risk).`);

  if (newConflicts.length > 0) {
    lines.push(`${newConflicts.length} new conflict(s) introduced.`);
  }
  if (resolvedConflicts.length > 0) {
    lines.push(`${resolvedConflicts.length} conflict(s) resolved.`);
  }

  return lines.join(" ");
}

/**
 * Generate a one-line quick summary.
 */
export function quickSimulationSummary(result: SimulationResult): string {
  return (
    `Simulation ${result.id}: ` +
    `${result.verdictChanges.length} changes, ` +
    `impact ${result.impactScore}/100 (${result.risk.level}), ` +
    `${result.newConflicts.length} new conflicts`
  );
}

// ─── Verdict Change Table ─────────────────────────────────────────────

/**
 * Format verdict changes as a summary table.
 */
export function formatVerdictChangeTable(changes: VerdictChange[]): string {
  if (changes.length === 0) {
    return "No verdict changes detected.";
  }

  const lines: string[] = [];
  lines.push("Request                    | Before    | After     | Category");
  lines.push("-".repeat(70));

  for (const change of changes) {
    const request = change.request.padEnd(25);
    const before = change.beforeEffect.padEnd(9);
    const after = change.afterEffect.padEnd(9);
    lines.push(`${request} | ${before} | ${after} | ${change.category}`);
  }

  return lines.join("\n");
}

// ─── Risk Assessment Reporting ─────────────────────────────────────────

/**
 * Detailed risk assessment from a simulation result.
 */
export interface RiskAssessment {
  level: SimulationRiskLevel;
  score: number;
  assessment: string;
  recommendations: string[];
}

/**
 * Generate a detailed risk assessment from a simulation result.
 */
export function assessSimulationRisk(result: SimulationResult): RiskAssessment {
  const recommendations: string[] = [];

  if (result.risk.newDenialsCount > 0) {
    recommendations.push(
      `Review ${result.risk.newDenialsCount} new denial(s) — affected workflows may break`,
    );
  }

  if (result.risk.newAllowancesCount > 0) {
    recommendations.push(
      `Review ${result.risk.newAllowancesCount} new allowance(s) — security posture may be weakened`,
    );
  }

  const criticalConflicts = result.newConflicts.filter((c) => c.severity === "critical").length;
  if (criticalConflicts > 0) {
    recommendations.push(
      `${criticalConflicts} critical conflict(s) detected — require approval before deployment`,
    );
  }

  if (result.complianceImpact && result.complianceImpact.scoreChange < 0) {
    recommendations.push(
      `Compliance score estimated to decrease by ${Math.abs(result.complianceImpact.scoreChange)} points`,
    );
  }

  const assessment =
    result.risk.level === "critical"
      ? "CRITICAL: This simulation poses significant risk and requires thorough review"
      : result.risk.level === "high"
        ? "HIGH: Notable impact detected — review recommended before proceeding"
        : result.risk.level === "medium"
          ? "MEDIUM: Moderate impact expected — standard review process sufficient"
          : "LOW: Minimal impact expected — safe to proceed with normal monitoring";

  return {
    level: result.risk.level,
    score: result.impactScore,
    assessment,
    recommendations,
  };
}
