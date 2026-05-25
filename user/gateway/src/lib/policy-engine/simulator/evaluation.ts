// ─── Zenic-Agents v3 — Simulation Evaluation ─────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Simulation Evaluation
//
// Provides evaluation logic for comparing before/after policy verdicts.
// Evaluates requests against policy sets and classifies verdict changes.
// Complements the runSimulation function in types.ts.
//
// Design Patterns:
//   - Memento: Before/after snapshots for verdict comparison
//   - Strategy: Impact scoring with configurable category weights

import type {
  PolicyDocument,
  PolicyEvaluationRequest,
  PolicyEvaluationResult,
  PolicyEffectV2,
  PolicyStatement,
  VerdictChangeCategory,
  VerdictChange,
} from "./types";

// ─── Evaluation Against Policy Set ────────────────────────────────────

/**
 * Evaluate a request against an array of policy documents.
 * Collects all matching statements across all documents,
 * sorts by priority (deny wins on tie), and returns the top match.
 */
export function evaluateAgainstPolicySet(
  evaluator: {
    evaluateDocument: (doc: PolicyDocument, req: PolicyEvaluationRequest) => PolicyEvaluationResult;
  },
  documents: PolicyDocument[],
  request: PolicyEvaluationRequest,
): PolicyEvaluationResult {
  const startTime = Date.now();
  const allMatched: PolicyEvaluationResult["matchedStatements"] = [];

  for (const doc of documents) {
    const result = evaluator.evaluateDocument(doc, request);
    allMatched.push(...result.matchedStatements);
  }

  // Sort by priority (highest first), deny wins on tie
  allMatched.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    const effectOrder: Record<string, number> = { deny: 0, conditional: 1, allow: 2 };
    return (effectOrder[a.effect] ?? 3) - (effectOrder[b.effect] ?? 3);
  });

  let finalEffect: PolicyEffectV2 = "deny";
  let matchReason = "No matching statement — default effect applied";
  let matchedStatementId: string | undefined;
  let matchedPolicyId = "default";
  let denyByDefault = true;
  let requiredRole: string | undefined;

  if (allMatched.length > 0) {
    const topMatch = allMatched[0]!;
    finalEffect = topMatch.effect;
    matchedStatementId = topMatch.statementId;
    matchedPolicyId = topMatch.policyId;
    denyByDefault = false;
    matchReason = `Matched statement "${topMatch.statementId}" in policy "${topMatch.policyId}" (priority ${topMatch.priority})`;

    for (const doc of documents) {
      if (doc.metadata.id === topMatch.policyId) {
        const stmt = doc.statements.find((s) => s.id === topMatch.statementId);
        if (stmt?.requiredRole) {
          requiredRole = stmt.requiredRole;
        }
        break;
      }
    }
  }

  return {
    effect: finalEffect,
    policyId: matchedPolicyId,
    matchedStatementId,
    reason: matchReason,
    matchedStatements: allMatched,
    duration: Date.now() - startTime,
    denyByDefault,
    requiredRole,
  };
}

// ─── Verdict Classification ───────────────────────────────────────────

/**
 * Classify the category of a verdict change based on before/after effects.
 *
 * Classification rules:
 *   NEW_DENY: allow/conditional → deny (CRITICAL)
 *   NEW_ALLOW: deny → allow (HIGH)
 *   NEW_CONDITIONAL: deny/allow → conditional (MEDIUM)
 *   CONDITIONAL_TO_DENY: conditional → deny (HIGH)
 *   CONDITIONAL_TO_ALLOW: conditional → allow (MEDIUM)
 *   EFFECT_UNCHANGED: same effect but different matched statement (LOW)
 */
export function classifyVerdictChange(
  beforeEffect: PolicyEffectV2,
  afterEffect: PolicyEffectV2,
): VerdictChangeCategory {
  if (beforeEffect === afterEffect) {
    return "effect_unchanged";
  }

  if (
    (beforeEffect === "allow" || beforeEffect === "conditional") &&
    afterEffect === "deny"
  ) {
    return "new_deny";
  }

  if (beforeEffect === "deny" && afterEffect === "allow") {
    return "new_allow";
  }

  if (
    (beforeEffect === "deny" || beforeEffect === "allow") &&
    afterEffect === "conditional"
  ) {
    return "new_conditional";
  }

  if (beforeEffect === "conditional" && afterEffect === "deny") {
    return "conditional_to_deny";
  }

  if (beforeEffect === "conditional" && afterEffect === "allow") {
    return "conditional_to_allow";
  }

  return "effect_unchanged";
}

/**
 * Generate a human-readable description for a verdict change.
 */
export function describeVerdictChange(
  request: string,
  beforeEffect: PolicyEffectV2,
  afterEffect: PolicyEffectV2,
  category: VerdictChangeCategory,
): string {
  const descriptions: Record<VerdictChangeCategory, string> = {
    new_deny:
      `[CRITICAL] ${request}: effect changed from ${beforeEffect} → ${afterEffect} (new denial introduced)`,
    new_allow:
      `[HIGH] ${request}: effect changed from ${beforeEffect} → ${afterEffect} (new allowance — security risk)`,
    new_conditional:
      `[MEDIUM] ${request}: effect changed from ${beforeEffect} → ${afterEffect} (now conditional)`,
    conditional_to_deny:
      `[HIGH] ${request}: effect changed from ${beforeEffect} → ${afterEffect} (conditional became denial)`,
    conditional_to_allow:
      `[MEDIUM] ${request}: effect changed from ${beforeEffect} → ${afterEffect} (conditional became allowance)`,
    effect_unchanged:
      `[LOW] ${request}: effect unchanged (${beforeEffect}) but matched different statement`,
  };
  return descriptions[category] ?? `${request}: ${beforeEffect} → ${afterEffect}`;
}

// ─── Impact Scoring ──────────────────────────────────────────────────

/**
 * Impact score weights per verdict change category.
 */
export const IMPACT_WEIGHTS: Record<VerdictChangeCategory, number> = {
  new_deny: 15,
  new_allow: 10,
  new_conditional: 5,
  conditional_to_deny: 10,
  conditional_to_allow: 5,
  effect_unchanged: 0,
};

/** Maximum impact score */
export const MAX_IMPACT_SCORE = 100;

/**
 * Calculate impact score based on verdict changes.
 * Each category has a configurable weight; total is capped at 100.
 */
export function calculateImpactScore(verdictChanges: VerdictChange[]): number {
  let score = 0;
  for (const change of verdictChanges) {
    score += IMPACT_WEIGHTS[change.category] ?? 0;
  }
  return Math.min(score, MAX_IMPACT_SCORE);
}

/**
 * Determine risk level from impact score.
 */
export function determineRiskLevel(score: number): string {
  if (score <= 20) return "low";
  if (score <= 50) return "medium";
  if (score <= 80) return "high";
  return "critical";
}

// ─── Causing Change Detection ─────────────────────────────────────────

/**
 * Find which proposed change likely caused a verdict difference.
 * Compares before/after results and tries to attribute the change
 * to a specific proposed modification.
 */
export function findCausingChange(
  request: PolicyEvaluationRequest,
  proposedChanges: SimulationChange[],
  evaluator: {
    evaluateDocument: (doc: PolicyDocument, req: PolicyEvaluationRequest) => PolicyEvaluationResult;
  },
  currentPolicies: PolicyDocument[],
  simulatedPolicies: PolicyDocument[],
): SimulationChange | undefined {
  // Simple heuristic: find the first change that affects the request's resource
  for (const change of proposedChanges) {
    // Check if the change targets a policy that matches the request
    if (change.policyId) {
      const currentDoc = currentPolicies.find((p) => p.metadata.id === change.policyId);
      const simDoc = simulatedPolicies.find((p) => p.metadata.id === change.policyId);

      if (currentDoc || simDoc) {
        // Check if any statement matches the request resource
        const doc = simDoc ?? currentDoc;
        if (doc) {
          const hasMatch = doc.statements.some(
            (s) =>
              (s.resource === "*" || s.resource === request.resource ||
                (s.resource.endsWith("/*") && request.resource.startsWith(s.resource.slice(0, -2)))) &&
              (s.action === "*" || s.action === request.action),
          );
          if (hasMatch) {
            return change;
          }
        }
      }
    }

    // Check new policy document
    if (change.document) {
      const hasMatch = change.document.statements.some(
        (s) =>
          (s.resource === "*" || s.resource === request.resource ||
            (s.resource.endsWith("/*") && request.resource.startsWith(s.resource.slice(0, -2)))) &&
          (s.action === "*" || s.action === request.action),
      );
      if (hasMatch) {
        return change;
      }
    }
  }

  return undefined;
}

/** Minimal type for SimulationChange */
interface SimulationChange {
  type: string;
  policyId?: string;
  document?: PolicyDocument;
}
