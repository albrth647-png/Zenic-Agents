// ─── Zenic-Agents v3 — Namespace Resolution ──────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Namespace Resolution
//
// Provides namespace resolution strategies for evaluating policies
// across namespace boundaries. Complements the evaluateInNamespace
// function in types.ts.
//
// Design Patterns:
//   - Strategy: pluggable resolution strategies
//   - Chain of Responsibility: namespace hierarchy evaluation

import type {
  PolicyDocument,
  PolicyEvaluationRequest,
  PolicyEvaluationResult,
  PolicyEffectV2,
  PolicyStatement,
  NamespaceResolutionStrategy,
  NamespaceHierarchy,
} from "./types";

// ─── Restrictiveness Ordering ─────────────────────────────────────────

const RESTRICTIVENESS_ORDER: Record<PolicyEffectV2, number> = {
  deny: 0,
  conditional: 1,
  allow: 2,
};

/**
 * Check if effect A is more restrictive than effect B.
 */
export function isMoreRestrictive(a: PolicyEffectV2, b: PolicyEffectV2): boolean {
  return (RESTRICTIVENESS_ORDER[a] ?? 3) < (RESTRICTIVENESS_ORDER[b] ?? 3);
}

// ─── Parent-Child Constraint Application ──────────────────────────────

/**
 * Apply parent-child hierarchy constraints on evaluation results.
 * Checks childCanOverrideParentDeny and childCanAddAllow constraints.
 */
export function applyParentChildConstraints(
  childResult: PolicyEvaluationResult,
  parentResult: PolicyEvaluationResult,
  hierarchy: NamespaceHierarchy,
): PolicyEvaluationResult {
  // If child says ALLOW but parent says DENY, and child cannot override
  if (
    childResult.effect === "allow" &&
    parentResult.effect === "deny" &&
    !hierarchy.childCanOverrideParentDeny
  ) {
    return {
      ...parentResult,
      reason: `Parent DENY overrides child ALLOW (childCanOverrideParentDeny=false): ${parentResult.reason}`,
    };
  }

  // If child adds ALLOW but is not allowed to
  if (
    childResult.effect === "allow" &&
    parentResult.effect !== "allow" &&
    !hierarchy.childCanAddAllow
  ) {
    return {
      ...parentResult,
      reason: `Child cannot add ALLOW rules (childCanAddAllow=false): parent effect ${parentResult.effect} preserved`,
    };
  }

  return childResult;
}

// ─── Resolution Strategies ────────────────────────────────────────────

/**
 * Conflict resolution strategy type for namespace boundaries.
 */
export type ConflictStrategy =
  | "deny_wins"
  | "priority_wins"
  | "merge_conditions"
  | "first_match"
  | "manual";

/**
 * Resolve conflicts between parent and child namespace results
 * using the parentChildResolution strategy.
 */
export function resolveParentChildConflict(
  childResult: PolicyEvaluationResult,
  parentResult: PolicyEvaluationResult,
  hierarchy: NamespaceHierarchy,
): PolicyEvaluationResult {
  const strategy = hierarchy.parentChildResolution as ConflictStrategy;

  switch (strategy) {
    case "deny_wins":
      if (childResult.effect === "deny" || parentResult.effect === "deny") {
        const denyResult = childResult.effect === "deny" ? childResult : parentResult;
        return {
          ...denyResult,
          reason: `DENY_WINS resolution: ${denyResult.reason}`,
        };
      }
      return childResult;

    case "priority_wins": {
      const childPrio = childResult.matchedStatements[0]?.priority ?? -1;
      const parentPrio = parentResult.matchedStatements[0]?.priority ?? -1;
      if (parentPrio > childPrio) {
        return {
          ...parentResult,
          reason: `PRIORITY_WINS resolution (parent priority ${parentPrio} > child ${childPrio}): ${parentResult.reason}`,
        };
      }
      return {
        ...childResult,
        reason: `PRIORITY_WINS resolution (child priority ${childPrio} >= parent ${parentPrio}): ${childResult.reason}`,
      };
    }

    case "merge_conditions": {
      if (isMoreRestrictive(parentResult.effect, childResult.effect)) {
        return {
          ...childResult,
          reason: `MERGE_CONDITIONS resolution (child more restrictive): ${childResult.reason}`,
        };
      }
      return {
        ...parentResult,
        reason: `MERGE_CONDITIONS resolution (parent more restrictive): ${parentResult.reason}`,
      };
    }

    case "first_match":
      return childResult;

    case "manual":
      return {
        ...childResult,
        reason: `MANUAL resolution required — child result preserved: ${childResult.reason}`,
      };

    default:
      return applyParentChildConstraints(childResult, parentResult, hierarchy);
  }
}

// ─── Resolution Result ────────────────────────────────────────────────

/**
 * Result of resolving a request across namespaces.
 */
export interface NamespaceResolutionResult {
  /** The namespace that resolved the request */
  resolvingNamespace: string;
  /** All namespaces consulted during resolution */
  consultedNamespaces: string[];
  /** The inheritance chain used */
  inheritanceChain: string[];
  /** The final evaluation result */
  evaluation: PolicyEvaluationResult;
  /** Whether a parent namespace was consulted */
  parentConsulted: boolean;
  /** Whether inherited rules affected the outcome */
  inheritedRulesApplied: boolean;
}

// ─── Multi-Namespace Resolution ───────────────────────────────────────

/**
 * Resolution result when evaluating across multiple sibling namespaces.
 */
export interface MultiNamespaceResolution {
  /** Results from each namespace */
  namespaceResults: Array<{
    namespaceId: string;
    result: PolicyEvaluationResult;
  }>;
  /** The final combined result */
  finalResult: PolicyEvaluationResult;
  /** The strategy used to combine results */
  strategy: NamespaceResolutionStrategy;
}

/**
 * Combine results from multiple namespaces using the specified strategy.
 */
export function combineNamespaceResults(
  namespaceResults: Array<{
    namespaceId: string;
    result: PolicyEvaluationResult;
  }>,
  strategy: NamespaceResolutionStrategy,
): PolicyEvaluationResult {
  if (namespaceResults.length === 0) {
    return {
      effect: "deny",
      policyId: "default",
      reason: "No namespace results to combine — default deny applied",
      matchedStatements: [],
      duration: 0,
      denyByDefault: true,
    };
  }

  if (namespaceResults.length === 1) {
    return namespaceResults[0]!.result;
  }

  switch (strategy) {
    case "local_first":
      return namespaceResults[0]!.result;

    case "deny_wins": {
      const denyResult = namespaceResults.find((nr) => nr.result.effect === "deny");
      if (denyResult) {
        return {
          ...denyResult.result,
          reason: `DENY_WINS across namespaces: ${denyResult.result.reason}`,
        };
      }
      return namespaceResults[0]!.result;
    }

    case "priority_based": {
      // Pick the result with the highest-priority matched statement
      let best = namespaceResults[0]!;
      for (const nr of namespaceResults.slice(1)) {
        const bestPrio = best.result.matchedStatements[0]?.priority ?? -1;
        const nrPrio = nr.result.matchedStatements[0]?.priority ?? -1;
        if (nrPrio > bestPrio) {
          best = nr;
        }
      }
      return best.result;
    }

    case "most_restrictive": {
      let mostRestrictive = namespaceResults[0]!;
      for (const nr of namespaceResults.slice(1)) {
        if (isMoreRestrictive(nr.result.effect, mostRestrictive.result.effect)) {
          mostRestrictive = nr;
        }
      }
      return mostRestrictive.result;
    }

    default:
      return namespaceResults[0]!.result;
  }
}

// ─── Resolution Strategy Description ──────────────────────────────────

/**
 * Get a human-readable description of a resolution strategy.
 */
export function describeResolutionStrategy(strategy: NamespaceResolutionStrategy): string {
  switch (strategy) {
    case "local_first":
      return "LOCAL_FIRST: Evaluate local namespace first, fall back to parent if no match";
    case "priority_based":
      return "PRIORITY_BASED: Collect all statements across hierarchy, highest priority wins";
    case "deny_wins":
      return "DENY_WINS: If any namespace returns deny, deny takes precedence";
    case "most_restrictive":
      return "MOST_RESTRICTIVE: The most restrictive effect across all namespaces wins";
    default:
      return `Unknown strategy: ${strategy}`;
  }
}
