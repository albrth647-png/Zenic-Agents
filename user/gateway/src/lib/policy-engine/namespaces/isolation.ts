// ─── Zenic-Agents v3 — Namespace Isolation ──────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Namespace Isolation
//
// Provides namespace isolation enforcement and boundary checking.
// Ensures policies in one namespace don't leak into another.
// Complements the namespace manager in types.ts.

import type {
  PolicyDocument,
  PolicyStatement,
  PolicyEffectV2,
} from "./types";

// ─── Isolation Level Types ────────────────────────────────────────────

/**
 * Isolation level for a namespace.
 *   - strict: No policy statements can cross namespace boundaries
 *   - moderate: Allow statements may cross but deny cannot
 *   - relaxed: All statements may cross unless explicitly blocked
 */
export type IsolationLevel = "strict" | "moderate" | "relaxed";

/**
 * Result of an isolation check.
 */
export interface IsolationCheckResult {
  /** Whether the statement is allowed to cross the boundary */
  allowed: boolean;
  /** Reason for the decision */
  reason: string;
  /** The isolation level that was applied */
  isolationLevel: IsolationLevel;
}

// ─── Isolation Enforcement ────────────────────────────────────────────

/**
 * Check if a statement is allowed to cross from one namespace to another.
 * Applies the isolation level of the source namespace.
 */
export function checkIsolationBoundary(
  statement: PolicyStatement,
  sourceIsolationLevel: IsolationLevel,
  sourceNamespace: string,
  targetNamespace: string,
): IsolationCheckResult {
  if (sourceNamespace === targetNamespace) {
    return {
      allowed: true,
      reason: "Same namespace — no boundary crossing",
      isolationLevel: sourceIsolationLevel,
    };
  }

  switch (sourceIsolationLevel) {
    case "strict":
      return {
        allowed: false,
        reason: `STRICT isolation: statement "${statement.id}" (${statement.effect}) cannot cross from "${sourceNamespace}" to "${targetNamespace}"`,
        isolationLevel: "strict",
      };

    case "moderate":
      // Allow statements may cross, deny cannot
      if (statement.effect === "allow") {
        return {
          allowed: true,
          reason: `MODERATE isolation: ALLOW statement "${statement.id}" may cross from "${sourceNamespace}" to "${targetNamespace}"`,
          isolationLevel: "moderate",
        };
      }
      return {
        allowed: false,
        reason: `MODERATE isolation: ${statement.effect.toUpperCase()} statement "${statement.id}" cannot cross from "${sourceNamespace}" to "${targetNamespace}"`,
        isolationLevel: "moderate",
      };

    case "relaxed":
      // All statements may cross unless explicitly blocked
      return {
        allowed: true,
        reason: `RELAXED isolation: statement "${statement.id}" (${statement.effect}) may cross from "${sourceNamespace}" to "${targetNamespace}"`,
        isolationLevel: "relaxed",
      };

    default:
      return {
        allowed: false,
        reason: `Unknown isolation level "${sourceIsolationLevel}" — defaulting to deny`,
        isolationLevel: sourceIsolationLevel,
      };
  }
}

// ─── Statement Filtering ──────────────────────────────────────────────

/**
 * Filter policy statements based on isolation boundaries.
 * Returns only the statements that are allowed to be visible from the target namespace.
 */
export function filterStatementsByIsolation(
  statements: PolicyStatement[],
  sourceIsolationLevel: IsolationLevel,
  sourceNamespace: string,
  targetNamespace: string,
): PolicyStatement[] {
  if (sourceNamespace === targetNamespace) {
    return statements; // Same namespace — no filtering needed
  }

  return statements.filter((stmt) => {
    const check = checkIsolationBoundary(stmt, sourceIsolationLevel, sourceNamespace, targetNamespace);
    return check.allowed;
  });
}

/**
 * Filter an entire policy document by isolation boundaries.
 * Returns a new document with only the allowed statements.
 */
export function filterDocumentByIsolation(
  document: PolicyDocument,
  sourceIsolationLevel: IsolationLevel,
  sourceNamespace: string,
  targetNamespace: string,
): PolicyDocument {
  if (sourceNamespace === targetNamespace) {
    return document;
  }

  const filteredStatements = filterStatementsByIsolation(
    document.statements,
    sourceIsolationLevel,
    sourceNamespace,
    targetNamespace,
  );

  return {
    ...document,
    statements: filteredStatements,
  };
}

// ─── Isolation Audit ─────────────────────────────────────────────────

/**
 * Isolation audit entry.
 */
export interface IsolationAuditEntry {
  sourceNamespace: string;
  targetNamespace: string;
  statementId: string;
  effect: PolicyEffectV2;
  allowed: boolean;
  reason: string;
}

/**
 * Audit all cross-namespace statement references.
 * Returns a list of all isolation boundary checks performed.
 */
export function auditIsolationBoundaries(
  policiesByNamespace: Map<string, { documents: PolicyDocument[]; isolationLevel: IsolationLevel }>,
  targetNamespace: string,
): IsolationAuditEntry[] {
  const audit: IsolationAuditEntry[] = [];

  for (const [nsId, { documents, isolationLevel }] of policiesByNamespace) {
    if (nsId === targetNamespace) continue;

    for (const doc of documents) {
      for (const stmt of doc.statements) {
        const check = checkIsolationBoundary(stmt, isolationLevel, nsId, targetNamespace);
        audit.push({
          sourceNamespace: nsId,
          targetNamespace,
          statementId: stmt.id,
          effect: stmt.effect,
          allowed: check.allowed,
          reason: check.reason,
        });
      }
    }
  }

  return audit;
}

// ─── Isolation Level Utilities ────────────────────────────────────────

/**
 * Parse an isolation level from a string.
 * Defaults to "moderate" for unrecognized values.
 */
export function parseIsolationLevel(value: string): IsolationLevel {
  if (value === "strict" || value === "moderate" || value === "relaxed") {
    return value;
  }
  return "moderate";
}

/**
 * Get the effective isolation level between two namespaces.
 * Uses the more restrictive of the two levels.
 */
export function effectiveIsolationLevel(
  levelA: IsolationLevel,
  levelB: IsolationLevel,
): IsolationLevel {
  const order: Record<IsolationLevel, number> = { strict: 0, moderate: 1, relaxed: 2 };
  const orderA = order[levelA] ?? 1;
  const orderB = order[levelB] ?? 1;

  // Return the more restrictive (lower number)
  return orderA <= orderB ? levelA : levelB;
}

/**
 * Check if one isolation level is more restrictive than another.
 */
export function isMoreRestrictiveLevel(a: IsolationLevel, b: IsolationLevel): boolean {
  const order: Record<IsolationLevel, number> = { strict: 0, moderate: 1, relaxed: 2 };
  return (order[a] ?? 1) < (order[b] ?? 1);
}
