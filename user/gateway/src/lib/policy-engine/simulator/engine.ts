// ─── Zenic-Agents v3 — Simulation Engine ──────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Simulation Engine
//
// Provides the core simulation engine for what-if policy analysis.
// Loads policies, applies proposed changes, and orchestrates the
// simulation pipeline. Complements the runSimulation function in types.ts.
//
// Design Patterns:
//   - Command: Each SimulationChange is a command that modifies the policy set
//   - Memento: Before/after snapshots for verdict comparison

import { db } from "@/lib/db";
import type {
  PolicyDocument,
  PolicyStatement,
  PolicyEffectV2,
  SimulationChange,
  SimulationChangeType,
} from "./types";

// ─── Deep Clone Helper ───────────────────────────────────────────────

/**
 * Deep clone a value using JSON serialization.
 * Safe for PolicyDocument trees which are plain JSON-compatible objects.
 */
export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

// ─── Change Application (Command Pattern) ─────────────────────────────

/**
 * Apply an ADD_POLICY change: add a new policy document to the simulated set.
 */
export function applyAddPolicy(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document) {
    console.warn("[Simulator] ADD_POLICY change missing document, skipping");
    return policies;
  }
  const exists = policies.some((p) => p.metadata.id === change.document!.metadata.id);
  if (exists) {
    console.warn(`[Simulator] ADD_POLICY: policy "${change.document.metadata.id}" already exists, replacing`);
    return policies.map((p) =>
      p.metadata.id === change.document!.metadata.id ? deepClone(change.document!) : p,
    );
  }
  return [...policies, deepClone(change.document)];
}

/**
 * Apply a MODIFY_POLICY change: replace an existing policy document entirely.
 */
export function applyModifyPolicy(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document) {
    console.warn("[Simulator] MODIFY_POLICY change missing document, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] MODIFY_POLICY: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  updated[idx] = deepClone(change.document);
  if (updated[idx]!.metadata.id !== change.policyId) {
    updated[idx]!.metadata.id = change.policyId;
  }
  return updated;
}

/**
 * Apply a REMOVE_POLICY change: remove a policy from the simulated set.
 */
export function applyRemovePolicy(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] REMOVE_POLICY: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  return policies.filter((p) => p.metadata.id !== change.policyId);
}

/**
 * Apply an ADD_STATEMENT change: add new statements to an existing policy.
 */
export function applyAddStatement(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document?.statements?.length) {
    console.warn("[Simulator] ADD_STATEMENT change missing statements, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] ADD_STATEMENT: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  const newStmts = deepClone(change.document.statements);
  updated[idx]!.statements.push(...newStmts);
  return updated;
}

/**
 * Apply a MODIFY_STATEMENT change: find and replace statements by ID.
 */
export function applyModifyStatement(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document?.statements?.length) {
    console.warn("[Simulator] MODIFY_STATEMENT change missing statements, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] MODIFY_STATEMENT: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  const replacements = deepClone(change.document.statements);
  for (const replacement of replacements) {
    const stmtIdx = updated[idx]!.statements.findIndex((s) => s.id === replacement.id);
    if (stmtIdx !== -1) {
      updated[idx]!.statements[stmtIdx] = replacement;
    } else {
      console.warn(
        `[Simulator] MODIFY_STATEMENT: statement "${replacement.id}" not found in policy "${change.policyId}"`,
      );
    }
  }
  return updated;
}

/**
 * Apply a REMOVE_STATEMENT change: remove statements by ID.
 */
export function applyRemoveStatement(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document?.statements?.length) {
    console.warn("[Simulator] REMOVE_STATEMENT change missing statements, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] REMOVE_STATEMENT: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  const idsToRemove = new Set(change.document.statements.map((s) => s.id));
  updated[idx]!.statements = updated[idx]!.statements.filter((s) => !idsToRemove.has(s.id));
  return updated;
}

/**
 * Apply a CHANGE_PRIORITY change: update a statement's priority.
 */
export function applyChangePriority(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document?.statements?.length) {
    console.warn("[Simulator] CHANGE_PRIORITY change missing statements, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] CHANGE_PRIORITY: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  for (const priorityChange of change.document.statements) {
    const stmtIdx = updated[idx]!.statements.findIndex((s) => s.id === priorityChange.id);
    if (stmtIdx !== -1) {
      updated[idx]!.statements[stmtIdx]!.priority = priorityChange.priority;
    } else {
      console.warn(
        `[Simulator] CHANGE_PRIORITY: statement "${priorityChange.id}" not found in policy "${change.policyId}"`,
      );
    }
  }
  return updated;
}

/**
 * Apply a CHANGE_CONDITION change: add/modify conditions on a statement.
 */
export function applyChangeCondition(
  policies: PolicyDocument[],
  change: SimulationChange,
): PolicyDocument[] {
  if (!change.document?.statements?.length) {
    console.warn("[Simulator] CHANGE_CONDITION change missing statements, skipping");
    return policies;
  }
  const idx = policies.findIndex((p) => p.metadata.id === change.policyId);
  if (idx === -1) {
    console.warn(`[Simulator] CHANGE_CONDITION: policy "${change.policyId}" not found, skipping`);
    return policies;
  }
  const updated = deepClone(policies);
  for (const condChange of change.document.statements) {
    const stmtIdx = updated[idx]!.statements.findIndex((s) => s.id === condChange.id);
    if (stmtIdx !== -1) {
      updated[idx]!.statements[stmtIdx]!.conditions = deepClone(condChange.conditions ?? []);
    } else {
      console.warn(
        `[Simulator] CHANGE_CONDITION: statement "${condChange.id}" not found in policy "${change.policyId}"`,
      );
    }
  }
  return updated;
}

/**
 * Apply all simulation changes to a policy set (Command pattern dispatcher).
 * Each change is applied sequentially in order.
 * Returns the modified policy set (original is not mutated).
 */
export function applySimulationChanges(
  currentPolicies: PolicyDocument[],
  changes: SimulationChange[],
): PolicyDocument[] {
  let policies = deepClone(currentPolicies);

  for (const change of changes) {
    switch (change.type) {
      case "add_policy" as SimulationChangeType:
        policies = applyAddPolicy(policies, change);
        break;
      case "modify_policy" as SimulationChangeType:
        policies = applyModifyPolicy(policies, change);
        break;
      case "remove_policy" as SimulationChangeType:
        policies = applyRemovePolicy(policies, change);
        break;
      case "add_statement" as SimulationChangeType:
        policies = applyAddStatement(policies, change);
        break;
      case "modify_statement" as SimulationChangeType:
        policies = applyModifyStatement(policies, change);
        break;
      case "remove_statement" as SimulationChangeType:
        policies = applyRemoveStatement(policies, change);
        break;
      case "change_priority" as SimulationChangeType:
        policies = applyChangePriority(policies, change);
        break;
      case "change_condition" as SimulationChangeType:
        policies = applyChangeCondition(policies, change);
        break;
      default:
        console.warn(`[Simulator] Unknown change type: ${change.type}, skipping`);
    }
  }

  return policies;
}

// ─── Policy Loading ───────────────────────────────────────────────────

/**
 * Load all active policies from the database.
 */
export async function loadActivePoliciesFromDb(): Promise<PolicyDocument[]> {
  const policies = await db.declPolicy.findMany({
    where: { isActive: true },
    orderBy: { updatedAt: "desc" },
  });

  return policies.map((p) => ({
    apiVersion: p.apiVersion,
    kind: "PolicyDocument" as const,
    metadata: {
      id: p.policyId,
      name: p.name,
      version: p.version,
      description: p.description,
      compliance: JSON.parse(p.compliance),
      labels: JSON.parse(p.labels),
      author: p.author ?? undefined,
      createdAt: p.createdAt.toISOString(),
      updatedAt: p.updatedAt.toISOString(),
    },
    statements: JSON.parse(p.statements),
    tests: JSON.parse(p.tests),
  }));
}

// ─── ID Generation ────────────────────────────────────────────────────

/**
 * Generate a unique simulation ID.
 */
export function generateSimulationId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 10);
  return `sim_${ts}_${rand}`;
}
