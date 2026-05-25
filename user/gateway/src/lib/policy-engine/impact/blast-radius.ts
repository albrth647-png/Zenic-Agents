// ─── Zenic-Agents v3 — Impact Blast Radius ────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Blast Radius Calculation
//
// Provides blast radius calculation utilities for impact analysis.
// Computes risk scores, estimates affected resources/users, and builds
// impact categories. Complements the analyzeImpact function in types.ts.

import type {
  PolicyEffectV2,
  DependencyRef,
  AffectedSetRef,
  AffectedPlaybookRef,
  AffectedToolRef,
  DownstreamChange,
  ImpactCategory,
  BlastRadius,
  SimulationRiskLevel,
} from "./types";

// ─── Blast Radius Calculation ─────────────────────────────────────────

/**
 * Calculate blast radius from analysis components.
 *
 * Risk score formula:
 *   - 10 points per direct dependency
 *   - 5 points per indirect dependency
 *   - 20 points per tool that changes from ALLOW → DENY
 *   - 15 points per tool that changes from DENY → ALLOW
 *   - 10 points per playbook with compliance score change
 *   - Cap at 100
 *
 * Risk levels:
 *   - 0-20: LOW
 *   - 21-50: MEDIUM
 *   - 51-80: HIGH
 *   - 81-100: CRITICAL
 *
 * Recovery time: riskScore * 2 minutes
 */
export function calculateBlastRadius(
  directDeps: DependencyRef[],
  indirectDeps: DependencyRef[],
  affectedSets: AffectedSetRef[],
  affectedPlaybooks: AffectedPlaybookRef[],
  affectedTools: AffectedToolRef[],
  downstreamChanges: DownstreamChange[],
  complianceStandardsImpacted: number,
): BlastRadius {
  let riskScore = 0;

  riskScore += directDeps.length * 10;
  riskScore += indirectDeps.length * 5;

  for (const change of downstreamChanges) {
    if (change.currentEffect === "allow" && change.predictedEffect === "deny") {
      riskScore += 20;
    } else if (change.currentEffect === "deny" && change.predictedEffect === "allow") {
      riskScore += 15;
    }
  }

  const playbooksWithComplianceChange = affectedPlaybooks.filter(
    (pb) => pb.complianceScoreChange !== 0,
  );
  riskScore += playbooksWithComplianceChange.length * 10;

  riskScore = Math.min(riskScore, 100);

  const riskLevel = determineRiskLevel(riskScore);

  const resourceIds = new Set<string>();
  for (const d of directDeps) resourceIds.add(`${d.type}:${d.id}`);
  for (const d of indirectDeps) resourceIds.add(`${d.type}:${d.id}`);
  for (const s of affectedSets) resourceIds.add(`policy_set:${s.setId}`);
  for (const p of affectedPlaybooks) resourceIds.add(`playbook:${p.playbookId}`);
  for (const t of affectedTools) resourceIds.add(`tool:${t.toolId}`);

  const estimatedUsers = estimateAffectedUsers(affectedTools, affectedPlaybooks);

  const categories = buildImpactCategories(
    affectedSets,
    affectedPlaybooks,
    affectedTools,
    downstreamChanges,
    complianceStandardsImpacted,
    estimatedUsers,
  );

  return {
    totalAffectedResources: resourceIds.size,
    totalAffectedUsers: estimatedUsers,
    riskScore,
    riskLevel,
    estimatedRecoveryMinutes: riskScore * 2,
    categories,
  };
}

// ─── Risk Level Determination ─────────────────────────────────────────

/**
 * Determine risk level from impact score.
 */
export function determineRiskLevel(score: number): SimulationRiskLevel {
  if (score <= 20) return "low";
  if (score <= 50) return "medium";
  if (score <= 80) return "high";
  return "critical";
}

// ─── User Estimation ──────────────────────────────────────────────────

/**
 * Estimate the number of affected users based on tool risk levels and playbook activations.
 */
export function estimateAffectedUsers(
  tools: AffectedToolRef[],
  playbooks: AffectedPlaybookRef[],
): number {
  let users = 0;

  for (const tool of tools) {
    switch (tool.riskLevel) {
      case "critical": users += 50; break;
      case "high": users += 30; break;
      case "medium": users += 15; break;
      default: users += 5; break;
    }
  }

  for (const pb of playbooks) {
    users += 20;
  }

  return users;
}

// ─── Impact Categories ────────────────────────────────────────────────

/**
 * Build impact categories for the blast radius.
 */
export function buildImpactCategories(
  sets: AffectedSetRef[],
  playbooks: AffectedPlaybookRef[],
  tools: AffectedToolRef[],
  changes: DownstreamChange[],
  complianceStandardsImpacted: number,
  estimatedUsers: number,
): ImpactCategory[] {
  const categories: ImpactCategory[] = [];

  if (sets.length > 0) {
    const maxPriority = Math.max(...sets.map((s) => s.priority), 0);
    categories.push({
      name: "Policy Sets",
      affectedCount: sets.length,
      severity: maxPriority >= 100 ? "critical" : maxPriority >= 50 ? "high" : "medium",
      description: `${sets.length} policy set(s) reference the target policy and may need re-composition`,
    });
  }

  if (playbooks.length > 0) {
    categories.push({
      name: "Playbooks",
      affectedCount: playbooks.length,
      severity: playbooks.length >= 5 ? "high" : playbooks.length >= 2 ? "medium" : "low",
      description: `${playbooks.length} playbook(s) activate this policy across industries`,
    });
  }

  const toolsWithVerdictChange = changes.length;
  if (toolsWithVerdictChange > 0 || tools.length > 0) {
    const allowToDeny = changes.filter(
      (c) => c.currentEffect === "allow" && c.predictedEffect === "deny",
    ).length;
    categories.push({
      name: "Tools",
      affectedCount: toolsWithVerdictChange || tools.length,
      severity: allowToDeny > 0 ? "critical" : toolsWithVerdictChange > 0 ? "high" : "medium",
      description: `${toolsWithVerdictChange} tool(s) with verdict changes, ${tools.length} total tools protected by this policy`,
    });
  }

  if (complianceStandardsImpacted > 0) {
    categories.push({
      name: "Compliance",
      affectedCount: complianceStandardsImpacted,
      severity: complianceStandardsImpacted >= 3 ? "critical" : complianceStandardsImpacted >= 2 ? "high" : "medium",
      description: `${complianceStandardsImpacted} compliance standard(s) may be impacted by this policy change`,
    });
  }

  if (estimatedUsers > 0) {
    categories.push({
      name: "Users",
      affectedCount: estimatedUsers,
      severity: estimatedUsers >= 100 ? "critical" : estimatedUsers >= 50 ? "high" : estimatedUsers >= 10 ? "medium" : "low",
      description: `Estimated ${estimatedUsers} user(s) affected by access changes`,
    });
  }

  return categories;
}

// ─── Verdict Simulation ───────────────────────────────────────────────

/**
 * Simple verdict simulation based on document statement matching.
 */
export function simulateVerdict(
  document: PolicyDocument,
  resourceName: string,
  actionName: string,
): PolicyEffectV2 {
  const matchedStatements = document.statements.filter((stmt) => {
    const resourceMatch = stmt.resource === "*" ||
      stmt.resource === resourceName ||
      (stmt.resource.endsWith("/*") && resourceName.startsWith(stmt.resource.slice(0, -2)));

    const actionMatch = stmt.action === "*" ||
      stmt.action === actionName;

    return resourceMatch && actionMatch;
  });

  if (matchedStatements.length === 0) {
    return "deny";
  }

  matchedStatements.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    const effectOrder: Record<string, number> = { deny: 0, conditional: 1, allow: 2 };
    return (effectOrder[a.effect] ?? 3) - (effectOrder[b.effect] ?? 3);
  });

  return matchedStatements[0]!.effect as PolicyEffectV2;
}

/** Minimal PolicyDocument type for local use */
interface PolicyDocument {
  statements: Array<{
    resource: string;
    action: string;
    effect: string;
    priority: number;
  }>;
}

// ─── Downstream Change Prediction ─────────────────────────────────────

/**
 * Predict downstream evaluation changes for affected tools.
 */
export function predictDownstreamChanges(
  currentDocument: { statements: PolicyStatement[] },
  proposedDocument: { statements: PolicyStatement[] } | undefined,
  affectedTools: AffectedToolRef[],
  depth: ImpactAnalysisDepth,
): DownstreamChange[] {
  const changes: DownstreamChange[] = [];

  if (!proposedDocument) {
    for (const tool of affectedTools) {
      changes.push({
        request: `tool:${tool.toolId}`,
        currentEffect: tool.currentVerdict,
        predictedEffect: "deny" as PolicyEffectV2,
        confidence: 0.6,
        reason: "Policy change may remove current access — deny-by-default fallback",
      });
    }
    return changes;
  }

  for (const tool of affectedTools) {
    const currentVerdict = tool.currentVerdict;
    const proposedVerdict = simulateVerdict(proposedDocument as PolicyDocument, tool.name, "execute");

    if (currentVerdict !== proposedVerdict) {
      changes.push({
        request: `tool:${tool.toolId}`,
        currentEffect: currentVerdict,
        predictedEffect: proposedVerdict,
        confidence: depth === "deep" ? 0.9 : depth === "standard" ? 0.75 : 0.6,
        reason: buildChangeReason(currentVerdict, proposedVerdict, tool.name),
      });
    }
  }

  return changes;
}

/** Minimal types for local use */
interface PolicyStatement {
  id: string;
  effect: string;
  resource: string;
  action: string;
  priority: number;
  conditions?: unknown[];
}

type ImpactAnalysisDepth = "quick" | "standard" | "deep";

/**
 * Build a human-readable reason for a verdict change.
 */
export function buildChangeReason(
  from: PolicyEffectV2,
  to: PolicyEffectV2,
  toolName: string,
): string {
  if (from === "allow" && to === "deny") {
    return `Tool "${toolName}" will be BLOCKED — access changes from ALLOW to DENY`;
  }
  if (from === "deny" && to === "allow") {
    return `Tool "${toolName}" will be OPENED — access changes from DENY to ALLOW`;
  }
  if (from === "allow" && to === "conditional") {
    return `Tool "${toolName}" will require CONDITIONAL approval instead of ALLOW`;
  }
  if (from === "deny" && to === "conditional") {
    return `Tool "${toolName}" will become CONDITIONAL instead of DENY`;
  }
  if (from === "conditional" && to === "deny") {
    return `Tool "${toolName}" will be BLOCKED — conditional access removed, now DENY`;
  }
  if (from === "conditional" && to === "allow") {
    return `Tool "${toolName}" will be fully ALLOWED — conditional restriction removed`;
  }
  return `Tool "${toolName}" verdict changes from ${from} to ${to}`;
}
