// ─── Zenic-Agents v3 — Namespace Manager ─────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Namespace Management
//
// Provides namespace management utilities: CRUD operations helpers,
// namespace hierarchy management, and policy assignment tracking.
// Complements the createNamespace/getNamespace functions in types.ts.

import { db } from "@/lib/db";
import type {
  PolicyNamespace,
  NamespaceHierarchy,
  NamespaceResolutionStrategy,
  NamespaceIsolationLevel,
  ConflictResolutionStrategy,
} from "./types";

// ─── DB Record Mapper ─────────────────────────────────────────────────

/** Internal representation of a namespace DB row mapped to typed fields */
export interface NamespaceDbRecord {
  id: string;
  namespaceId: string;
  name: string;
  description: string;
  tenantId: string;
  parentNamespaceId: string | null;
  path: string;
  labels: Record<string, string>;
  inheritFromParent: boolean;
  maxInheritanceDepth: number;
  parentChildResolution: ConflictResolutionStrategy;
  childCanOverrideParentDeny: boolean;
  childCanAddAllow: boolean;
  resolutionStrategy: NamespaceResolutionStrategy;
  isolationLevel: NamespaceIsolationLevel;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Map a raw DB row to a NamespaceDbRecord.
 */
export function mapDbToRecord(row: {
  id: string;
  namespaceId: string;
  name: string;
  description: string;
  tenantId: string;
  parentNamespaceId: string | null;
  path: string;
  labels: string;
  inheritFromParent: boolean;
  maxInheritanceDepth: number;
  parentChildResolution: string;
  childCanOverrideParentDeny: boolean;
  childCanAddAllow: boolean;
  resolutionStrategy: string;
  isolationLevel: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}): NamespaceDbRecord {
  return {
    id: row.id,
    namespaceId: row.namespaceId,
    name: row.name,
    description: row.description,
    tenantId: row.tenantId,
    parentNamespaceId: row.parentNamespaceId,
    path: row.path,
    labels: JSON.parse(row.labels),
    inheritFromParent: row.inheritFromParent,
    maxInheritanceDepth: row.maxInheritanceDepth,
    parentChildResolution: row.parentChildResolution as ConflictResolutionStrategy,
    childCanOverrideParentDeny: row.childCanOverrideParentDeny,
    childCanAddAllow: row.childCanAddAllow,
    resolutionStrategy: row.resolutionStrategy as NamespaceResolutionStrategy,
    isolationLevel: row.isolationLevel as NamespaceIsolationLevel,
    isActive: row.isActive,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

/**
 * Map a NamespaceDbRecord to a PolicyNamespace type.
 */
export function mapRecordToPolicyNamespace(rec: NamespaceDbRecord): PolicyNamespace {
  return {
    apiVersion: "namespace.zenic.dev/v1",
    kind: "Namespace",
    metadata: {
      id: rec.namespaceId,
      name: rec.name,
      description: rec.description,
      tenantId: rec.tenantId,
      parentNamespaceId: rec.parentNamespaceId ?? undefined,
      path: rec.path,
      labels: rec.labels,
      createdAt: rec.createdAt.toISOString(),
      updatedAt: rec.updatedAt.toISOString(),
    },
    hierarchy: {
      inheritFromParent: rec.inheritFromParent,
      maxInheritanceDepth: rec.maxInheritanceDepth,
      parentChildResolution: rec.parentChildResolution,
      childCanOverrideParentDeny: rec.childCanOverrideParentDeny,
      childCanAddAllow: rec.childCanAddAllow,
    },
    resolutionStrategy: rec.resolutionStrategy,
    isolationLevel: rec.isolationLevel,
  };
}

// ─── Namespace Hierarchy Helpers ──────────────────────────────────────

/**
 * Load a namespace record from DB by namespaceId.
 */
export async function loadNamespaceRecord(namespaceId: string): Promise<NamespaceDbRecord | null> {
  const row = await db.policyNamespace.findFirst({
    where: { namespaceId },
  });
  if (!row) return null;
  return mapDbToRecord(row);
}

/**
 * Compute the depth of a namespace in the hierarchy.
 */
export async function computeDepth(namespaceId: string): Promise<number> {
  let depth = 0;
  let currentId: string | null | undefined = namespaceId;
  const visited = new Set<string>();

  while (currentId) {
    if (visited.has(currentId)) break;
    visited.add(currentId);

    const rec = await loadNamespaceRecord(currentId);
    if (!rec) break;
    currentId = rec.parentNamespaceId;
    if (currentId) depth++;
  }

  return depth;
}

/**
 * Build the namespace path from root to this namespace.
 */
export async function buildNamespacePath(namespaceId: string): Promise<string> {
  const chain: string[] = [];
  let currentId: string | null = namespaceId;
  const visited = new Set<string>();

  while (currentId) {
    if (visited.has(currentId)) break;
    visited.add(currentId);

    const rec = await loadNamespaceRecord(currentId);
    if (!rec) break;
    chain.unshift(rec.namespaceId);
    currentId = rec.parentNamespaceId;
  }

  return chain.join("/");
}

// ─── Namespace Policy Loading ─────────────────────────────────────────

/** Maximum policies to load per namespace */
const MAX_POLICIES_PER_NAMESPACE = 200;

/**
 * Load all PolicyDocuments associated with a namespace.
 * Searches by labels and PolicySet.namespace field.
 */
export async function loadNamespacePolicies(
  namespaceId: string,
  tenantId: string,
): Promise<Array<import("./types").PolicyDocument>> {
  const policies: Array<import("./types").PolicyDocument> = [];
  const seenPolicyIds = new Set<string>();

  // 1. Load policies via DeclPolicy labels
  const labeledPolicies = await db.declPolicy.findMany({
    where: {
      isActive: true,
      OR: [
        { labels: { contains: `"namespace":"${namespaceId}"` } },
        { labels: { contains: `"zenic.dev/namespace":"${namespaceId}"` } },
      ],
    },
    take: MAX_POLICIES_PER_NAMESPACE,
  });

  for (const p of labeledPolicies) {
    if (seenPolicyIds.has(p.policyId)) continue;
    try {
      const labels = JSON.parse(p.labels) as Record<string, string>;
      seenPolicyIds.add(p.policyId);
      policies.push({
        apiVersion: p.apiVersion,
        kind: "PolicyDocument" as const,
        metadata: {
          id: p.policyId,
          name: p.name,
          version: p.version,
          description: p.description,
          compliance: JSON.parse(p.compliance),
          labels,
          author: p.author ?? undefined,
          createdAt: p.createdAt.toISOString(),
          updatedAt: p.updatedAt.toISOString(),
        },
        statements: JSON.parse(p.statements),
        tests: JSON.parse(p.tests),
      });
    } catch {
      // Skip policies with malformed labels
    }
  }

  // 2. Load policies via PolicySet.namespace field
  const policySets = await db.policySet.findMany({
    where: {
      namespace: namespaceId,
      isActive: true,
    },
  });

  for (const set of policySets) {
    try {
      const entries = JSON.parse(set.policies) as Array<{ policyId: string; version?: string }>;
      const policyIds = entries
        .map((e) => e.policyId)
        .filter((id) => !seenPolicyIds.has(id));

      if (policyIds.length > 0) {
        const batchPolicies = await db.declPolicy.findMany({
          where: {
            policyId: { in: policyIds },
            isActive: true,
          },
          take: MAX_POLICIES_PER_NAMESPACE - policies.length,
        });

        for (const policy of batchPolicies) {
          if (seenPolicyIds.has(policy.policyId)) continue;
          seenPolicyIds.add(policy.policyId);
          policies.push({
            apiVersion: policy.apiVersion,
            kind: "PolicyDocument" as const,
            metadata: {
              id: policy.policyId,
              name: policy.name,
              version: policy.version,
              description: policy.description,
              compliance: JSON.parse(policy.compliance),
              labels: JSON.parse(policy.labels),
              author: policy.author ?? undefined,
              createdAt: policy.createdAt.toISOString(),
              updatedAt: policy.updatedAt.toISOString(),
            },
            statements: JSON.parse(policy.statements),
            tests: JSON.parse(policy.tests),
          });
        }
      }
    } catch {
      // Skip sets with malformed policy entries
    }
  }

  return policies;
}

// ─── Namespace Statistics ─────────────────────────────────────────────

/**
 * Statistics about a namespace.
 */
export interface NamespaceStats {
  namespaceId: string;
  name: string;
  depth: number;
  policyCount: number;
  childCount: number;
  hasParent: boolean;
  inheritFromParent: boolean;
  resolutionStrategy: NamespaceResolutionStrategy;
  isolationLevel: NamespaceIsolationLevel;
}

/**
 * Compute statistics for a namespace.
 */
export async function getNamespaceStats(namespaceId: string): Promise<NamespaceStats | null> {
  const rec = await loadNamespaceRecord(namespaceId);
  if (!rec) return null;

  const depth = await computeDepth(namespaceId);
  const policies = await loadNamespacePolicies(namespaceId, rec.tenantId);

  const children = await db.policyNamespace.findMany({
    where: {
      parentNamespaceId: namespaceId,
      isActive: true,
    },
  });

  return {
    namespaceId: rec.namespaceId,
    name: rec.name,
    depth,
    policyCount: policies.length,
    childCount: children.length,
    hasParent: rec.parentNamespaceId !== null,
    inheritFromParent: rec.inheritFromParent,
    resolutionStrategy: rec.resolutionStrategy,
    isolationLevel: rec.isolationLevel,
  };
}
