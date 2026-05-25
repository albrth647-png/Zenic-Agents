// ─── Zenic-Agents v3 — Namespace Inheritance ─────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Namespace Inheritance
//
// Provides namespace inheritance traversal and evaluation logic.
// Walks up the namespace hierarchy to resolve policies via inheritance.
// Complements the evaluateInNamespace function in types.ts.
//
// Design Patterns:
//   - Chain of Responsibility: namespace hierarchy evaluation
//   - Composite: namespace tree with parent-child relationships

import type {
  PolicyDocument,
  PolicyEvaluationRequest,
  PolicyEvaluationResult,
  PolicyEffectV2,
  PolicyStatement,
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

/**
 * Get the most restrictive effect from a list.
 */
export function mostRestrictiveEffect(effects: PolicyEffectV2[]): PolicyEffectV2 {
  if (effects.length === 0) return "deny";

  let result: PolicyEffectV2 = effects[0]!;
  for (let i = 1; i < effects.length; i++) {
    if (isMoreRestrictive(effects[i]!, result)) {
      result = effects[i]!;
    }
  }
  return result;
}

/**
 * Get the least restrictive effect from a list.
 */
export function leastRestrictiveEffect(effects: PolicyEffectV2[]): PolicyEffectV2 {
  if (effects.length === 0) return "deny";

  let result: PolicyEffectV2 = effects[0]!;
  for (let i = 1; i < effects.length; i++) {
    if (!isMoreRestrictive(effects[i]!, result)) {
      result = effects[i]!;
    }
  }
  return result;
}

// ─── Inheritance Chain ────────────────────────────────────────────────

/**
 * Namespace node in an inheritance chain.
 */
export interface InheritanceNode {
  namespaceId: string;
  name: string;
  path: string;
  depth: number;
  parentNamespaceId: string | null;
  inheritFromParent: boolean;
  maxInheritanceDepth: number;
  policies: PolicyDocument[];
}

/**
 * Build an inheritance chain from a list of namespace records.
 * Returns ordered from root to leaf.
 */
export function buildInheritanceChain(
  nodes: Array<{
    namespaceId: string;
    name: string;
    path: string;
    parentNamespaceId: string | null;
    inheritFromParent: boolean;
    maxInheritanceDepth: number;
  }>,
  targetNamespaceId: string,
): InheritanceNode[] {
  const chain: InheritanceNode[] = [];
  const nodeMap = new Map(nodes.map((n) => [n.namespaceId, n]));

  let currentId: string | null = targetNamespaceId;
  const visited = new Set<string>();
  let depth = 0;

  // Walk up from target to root
  const reverseChain: InheritanceNode[] = [];
  while (currentId) {
    if (visited.has(currentId)) break; // Circular reference guard
    visited.add(currentId);

    const node = nodeMap.get(currentId);
    if (!node) break;

    reverseChain.push({
      namespaceId: node.namespaceId,
      name: node.name,
      path: node.path,
      depth,
      parentNamespaceId: node.parentNamespaceId,
      inheritFromParent: node.inheritFromParent,
      maxInheritanceDepth: node.maxInheritanceDepth,
      policies: [],
    });

    depth++;
    currentId = node.parentNamespaceId;
  }

  // Reverse to get root-first order
  reverseChain.reverse();

  // Recalculate depths (root = 0)
  for (let i = 0; i < reverseChain.length; i++) {
    reverseChain[i]!.depth = i;
  }

  chain.push(...reverseChain);
  return chain;
}

// ─── Inheritance Resolution ───────────────────────────────────────────

/**
 * Result of resolving a request through the inheritance chain.
 */
export interface InheritanceResolution {
  /** Final evaluation result */
  result: PolicyEvaluationResult;
  /** Which namespace provided the winning result */
  resolvingNamespaceId: string;
  /** All namespaces consulted in order */
  consultedNamespaces: string[];
  /** Whether a parent namespace was consulted */
  parentConsulted: boolean;
  /** Whether inherited rules affected the outcome */
  inheritedRulesApplied: boolean;
}

/**
 * Evaluate a request against an inheritance chain (LOCAL_FIRST strategy).
 * Walks from the target namespace up to root, stopping at the first
 * definitive result.
 */
export function evaluateLocalFirstInChain(
  chain: InheritanceNode[],
  request: PolicyEvaluationRequest,
  evaluator: { evaluateDocument: (doc: PolicyDocument, req: PolicyEvaluationRequest) => PolicyEvaluationResult },
): InheritanceResolution {
  let resolvingNamespaceId = chain[chain.length - 1]?.namespaceId ?? "unknown";
  const consultedNamespaces: string[] = [];
  let parentConsulted = false;
  let inheritedRulesApplied = false;

  // Evaluate from leaf (target) up to root
  for (let i = chain.length - 1; i >= 0; i--) {
    const node = chain[i]!;

    if (node.policies.length === 0 && node.inheritFromParent) {
      consultedNamespaces.push(node.namespaceId);
      parentConsulted = true;
      continue;
    }

    for (const policy of node.policies) {
      const evalResult = evaluator.evaluateDocument(policy, request);
      consultedNamespaces.push(node.namespaceId);

      if (!evalResult.denyByDefault) {
        // Got a definitive result
        if (i < chain.length - 1) {
          parentConsulted = true;
          inheritedRulesApplied = true;
        }
        resolvingNamespaceId = node.namespaceId;

        return {
          result: evalResult,
          resolvingNamespaceId,
          consultedNamespaces,
          parentConsulted,
          inheritedRulesApplied,
        };
      }
    }

    // No definitive result at this level — continue up
    if (node.inheritFromParent && i > 0) {
      parentConsulted = true;
    } else {
      break; // Inheritance disabled or no parent
    }
  }

  // No result found — deny by default
  return {
    result: {
      effect: "deny",
      policyId: "default",
      reason: "No matching policy in namespace hierarchy — default deny applied",
      matchedStatements: [],
      duration: 0,
      denyByDefault: true,
    },
    resolvingNamespaceId,
    consultedNamespaces,
    parentConsulted,
    inheritedRulesApplied,
  };
}

// ─── Hierarchy Validation ────────────────────────────────────────────

/**
 * Validate a namespace hierarchy for consistency.
 * Checks for circular references, depth limits, and parent existence.
 */
export function validateHierarchy(
  namespaces: Array<{
    namespaceId: string;
    parentNamespaceId: string | null;
    maxInheritanceDepth: number;
  }>,
): { valid: boolean; errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const nsMap = new Map(namespaces.map((n) => [n.namespaceId, n]));

  for (const ns of namespaces) {
    // Check parent exists
    if (ns.parentNamespaceId && !nsMap.has(ns.parentNamespaceId)) {
      errors.push(`Namespace "${ns.namespaceId}" references non-existent parent "${ns.parentNamespaceId}"`);
    }

    // Check for circular references
    const visited = new Set<string>();
    let currentId: string | null = ns.namespaceId;
    let depth = 0;

    while (currentId) {
      if (visited.has(currentId)) {
        errors.push(`Circular reference detected starting at namespace "${ns.namespaceId}"`);
        break;
      }
      visited.add(currentId);

      const current = nsMap.get(currentId);
      if (!current) break;

      depth++;
      if (depth > current.maxInheritanceDepth && current.maxInheritanceDepth > 0) {
        warnings.push(`Namespace "${ns.namespaceId}" hierarchy exceeds maxInheritanceDepth of ${current.maxInheritanceDepth}`);
        break;
      }

      currentId = current.parentNamespaceId;
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}
