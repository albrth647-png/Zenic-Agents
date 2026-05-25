// ─── Zenic-Agents v3 — Impact Analyzer ────────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Impact Analysis
//
// Provides impact analysis utilities for predicting the downstream
// effects of policy changes. Complements the analyzeImpact function in types.ts.
//
// Design Patterns:
//   - Visitor: DependencyGraphVisitor traverses the dependency graph
//   - Strategy: DepthStrategy determines analysis depth
//   - Composite: DependencyNode composes dependency tree with children

import { db } from "@/lib/db";
import type {
  PolicyDocument,
  PolicyStatement,
  PolicyEffectV2,
  PolicySetEntry,
  ImpactAnalysisDepth,
  ImpactAnalysisRequest,
  ImpactAnalysisResult,
  DependencyRef,
  AffectedSetRef,
  AffectedPlaybookRef,
  AffectedToolRef,
  DownstreamChange,
  ImpactCategory,
  BlastRadius,
  SimulationRiskLevel,
} from "./types";

// ─── Dependency Node (Composite Pattern) ──────────────────────────────

/** A node in the dependency tree */
export interface DependencyNode {
  id: string;
  type: "policy" | "policy_set" | "playbook" | "tool" | "approval";
  name: string;
  dependencyType: string;
  hardDependency: boolean;
  children: DependencyNode[];
  data?: unknown;
}

/** Build a DependencyRef from a DependencyNode */
export function nodeToRef(node: DependencyNode): DependencyRef {
  return {
    id: node.id,
    type: node.type,
    name: node.name,
    dependencyType: node.dependencyType,
    hardDependency: node.hardDependency,
  };
}

// ─── Depth Strategy (Strategy Pattern) ────────────────────────────────

/** Strategy interface for analysis depth */
export interface DepthStrategy {
  includeIndirect: boolean;
  maxIndirectionLevels: number;
  predictToolChanges: boolean;
  includeComplianceChanges: boolean;
}

/** Strategy configuration per analysis depth */
export const DEPTH_STRATEGIES: Record<string, DepthStrategy> = {
  quick: {
    includeIndirect: false,
    maxIndirectionLevels: 0,
    predictToolChanges: true,
    includeComplianceChanges: false,
  },
  standard: {
    includeIndirect: true,
    maxIndirectionLevels: 1,
    predictToolChanges: true,
    includeComplianceChanges: true,
  },
  deep: {
    includeIndirect: true,
    maxIndirectionLevels: -1,
    predictToolChanges: true,
    includeComplianceChanges: true,
  },
};

// ─── Policy Loading ───────────────────────────────────────────────────

/**
 * Load a policy document from DB by policyId.
 */
export async function loadPolicyFromDb(policyId: string): Promise<PolicyDocument | null> {
  try {
    const record = await db.declPolicy.findUnique({
      where: { policyId },
    });

    if (!record) return null;

    return {
      apiVersion: record.apiVersion,
      kind: "PolicyDocument",
      metadata: {
        id: record.policyId,
        name: record.name,
        version: record.version,
        description: record.description,
        compliance: JSON.parse(record.compliance),
        labels: JSON.parse(record.labels),
        author: record.author ?? undefined,
        createdAt: record.createdAt.toISOString(),
        updatedAt: record.updatedAt.toISOString(),
      },
      statements: JSON.parse(record.statements),
      tests: JSON.parse(record.tests),
    };
  } catch (error) {
    console.error(`[ImpactAnalysis] Failed to load policy ${policyId}:`, error);
    return null;
  }
}

// ─── Direct Dependency Finding ────────────────────────────────────────

/**
 * Find PolicySets that reference the given policy.
 */
export async function findReferencingPolicySets(policyId: string): Promise<Array<{
  id: string;
  setId: string;
  name: string;
  policies: string;
  entry: PolicySetEntry;
}>> {
  const results: Array<{
    id: string;
    setId: string;
    name: string;
    policies: string;
    entry: PolicySetEntry;
  }> = [];

  try {
    const policySets = await db.policySet.findMany({
      where: { isActive: true },
    });

    for (const ps of policySets) {
      const entries: PolicySetEntry[] = JSON.parse(ps.policies);
      const matchingEntry = entries.find((e) => e.policyId === policyId);
      if (matchingEntry) {
        results.push({
          id: ps.id,
          setId: ps.setId,
          name: ps.name,
          policies: ps.policies,
          entry: matchingEntry,
        });
      }
    }
  } catch (error) {
    console.error("[ImpactAnalysis] Failed to find referencing policy sets:", error);
  }

  return results;
}

/**
 * Find Playbooks that activate the given policy.
 */
export async function findReferencingPlaybooks(policyId: string): Promise<Array<{
  playbookId: string;
  name: string;
  industry: string;
  policies: string;
  subIndustry: string | null;
}>> {
  const results: Array<{
    playbookId: string;
    name: string;
    industry: string;
    policies: string;
    subIndustry: string | null;
  }> = [];

  try {
    const playbooks = await db.playbook.findMany({
      where: { isActive: true },
    });

    for (const pb of playbooks) {
      const policyRefs = JSON.parse(pb.policies) as Array<{ policyId: string; role?: string }>;
      if (policyRefs.some((ref) => ref.policyId === policyId)) {
        results.push({
          playbookId: pb.playbookId,
          name: pb.name,
          industry: pb.industry,
          policies: pb.policies,
          subIndustry: pb.subIndustry,
        });
      }
    }
  } catch (error) {
    console.error("[ImpactAnalysis] Failed to find referencing playbooks:", error);
  }

  return results;
}

/**
 * Find approval requests targeting this policy.
 */
export async function findReferencingApprovals(policyId: string): Promise<Array<{
  approvalId: string;
  title: string;
  status: string;
  priority: string;
  requestedBy: string;
}>> {
  const results: Array<{
    approvalId: string;
    title: string;
    status: string;
    priority: string;
    requestedBy: string;
  }> = [];

  try {
    const approvals = await db.policyApproval.findMany({
      where: { targetPolicyId: policyId },
    });

    for (const a of approvals) {
      results.push({
        approvalId: a.approvalId,
        title: a.title,
        status: a.status,
        priority: a.priority,
        requestedBy: a.requestedBy,
      });
    }
  } catch (error) {
    console.error("[ImpactAnalysis] Failed to find referencing approvals:", error);
  }

  return results;
}

// ─── ID Generation ────────────────────────────────────────────────────

/**
 * Generate a unique analysis ID.
 */
export function generateAnalysisId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 10);
  return `impact_${ts}_${rand}`;
}
