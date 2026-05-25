import { db } from "@/lib/db";
import type { PolicyDocument, PolicyApprovalRequest, ApprovalStatus, ApprovalPriority, ApprovalDecision, AutoApproveRule, AutoApproveCondition } from "../types";
import {
  ApprovalStatus as ApprovalStatusEnum,
  ApprovalPriority as ApprovalPriorityEnum,
} from "../types/approval";
import { AUTO_APPROVE_CHECKERS, AutoApproveRuleChecker } from "./types";
import type { CreateApprovalRequestInput, ApprovalListOptions } from "./types";
import { validateProposedDocument } from "./auto-approve";

// ─── Auto-Approve Rule Evaluation ────────────────────────────────────

/**
 * Evaluate all auto-approve rules against the proposed change.
 * Chain of Responsibility: each rule is evaluated; all enabled rules must pass.
 * Returns true if all active rules pass — auto-approve.
 */
function evaluateAutoApproveRules(
  rules: AutoApproveRule[],
  proposedDocument: PolicyDocument,
  existingDocument: PolicyDocument | null,
): boolean {
  const enabledRules = rules.filter((r) => r.enabled);
  if (enabledRules.length === 0) return false;

  for (const rule of enabledRules) {
    const rulePasses = evaluateSingleRule(rule, proposedDocument, existingDocument);
    if (!rulePasses) return false;
  }
  return true;
}

/**
 * Evaluate a single auto-approve rule.
 * All specified conditions in the rule must pass.
 */
function evaluateSingleRule(
  rule: AutoApproveRule,
  proposedDocument: PolicyDocument,
  existingDocument: PolicyDocument | null,
): boolean {
  const condition = rule.condition;
  for (const checker of AUTO_APPROVE_CHECKERS) {
    const fieldValue = condition[checker.field];
    if (fieldValue !== undefined && fieldValue !== null) {
      if (!checker.check(fieldValue, proposedDocument, existingDocument)) {
        return false;
      }
    }
  }
  return true;
}

// ─── Required Approvals Calculation ──────────────────────────────────

/** Priority-based default approval counts */
const PRIORITY_APPROVAL_MAP: Record<string, number> = {
  low: 1,
  medium: 1,
  high: 2,
  critical: 2,
  emergency: 1,
};

/** Default reviewer roles by priority */
const PRIORITY_REVIEWER_ROLES: Record<string, string[]> = {
  low: ["policy_reviewer"],
  medium: ["policy_reviewer"],
  high: ["policy_reviewer", "policy_admin"],
  critical: ["policy_admin", "compliance_officer"],
  emergency: ["policy_admin"],
};

/**
 * Calculate the required number of approvals based on policy risk.
 * Factors: priority, number of deny statements, compliance standards involved.
 */
function calculateRequiredApprovals(
  proposedDocument: PolicyDocument,
  priority: ApprovalPriority,
): number {
  let required = PRIORITY_APPROVAL_MAP[priority] ?? 1;

  // Additional approval for policies with many deny statements
  const denyCount = proposedDocument.statements.filter(
    (s) => s.effect === "deny"
  ).length;
  if (denyCount >= 3) {
    required += 1;
  }

  // Additional approval for policies touching compliance standards
  const compliance = proposedDocument.metadata.compliance ?? [];
  if (compliance.length >= 2) {
    required += 1;
  }

  return required;
}

/**
 * Calculate required reviewer roles based on priority and document content.
 */
function calculateRequiredReviewerRoles(
  proposedDocument: PolicyDocument,
  priority: ApprovalPriority,
): string[] {
  const roles = [...(PRIORITY_REVIEWER_ROLES[priority] ?? ["policy_reviewer"])];

  // Add compliance officer if compliance standards are involved
  const compliance = proposedDocument.metadata.compliance ?? [];
  if (compliance.length > 0 && !roles.includes("compliance_officer")) {
    roles.push("compliance_officer");
  }

  return roles;
}

// ─── DB Domain Mapping ─────────────────────────────────────────────

/**
 * Map a Prisma PolicyApproval record to the domain PolicyApprovalRequest.
 */
function mapDbToApprovalRequest(record: {
  id: string;
  approvalId: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  targetPolicyId: string | null;
  previousVersion: string | null;
  proposedDocument: string;
  simulationId: string | null;
  requestedBy: string;
  requiredApprovals: number;
  currentApprovals: number;
  approvals: string;
  requiredReviewerRoles: string;
  autoApproveRules: string;
  autoApproved: boolean;
  expiresAt: Date | null;
  deployedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}): PolicyApprovalRequest {
  return {
    id: record.approvalId,
    title: record.title,
    description: record.description,
    status: record.status as ApprovalStatus,
    priority: record.priority as ApprovalPriority,
    proposedDocument: JSON.parse(record.proposedDocument) as PolicyDocument,
    targetPolicyId: record.targetPolicyId ?? undefined,
    previousVersion: record.previousVersion ?? undefined,
    simulationId: record.simulationId ?? undefined,
    requestedBy: record.requestedBy,
    requiredApprovals: record.requiredApprovals,
    approvals: JSON.parse(record.approvals) as ApprovalDecision[],
    requiredReviewerRoles: JSON.parse(record.requiredReviewerRoles) as string[],
    autoApproveRules: JSON.parse(record.autoApproveRules) as AutoApproveRule[],
    autoApproved: record.autoApproved,
    expiresAt: record.expiresAt?.toISOString() ?? undefined,
    createdAt: record.createdAt.toISOString(),
    updatedAt: record.updatedAt.toISOString(),
    deployedAt: record.deployedAt?.toISOString() ?? undefined,
  };
}

/**
 * Load the existing PolicyDocument for a target policy (if any).
 */
async function loadExistingDocument(
  targetPolicyId?: string | null,
): Promise<PolicyDocument | null> {
  if (!targetPolicyId) return null;

  const policy = await db.declPolicy.findUnique({
    where: { policyId: targetPolicyId },
  });
  if (!policy) return null;

  try {
    const activeVersion = await db.declPolicyVersion.findFirst({
      where: { declPolicyId: policy.id, status: "active" },
      orderBy: { createdAt: "desc" },
    });

    if (activeVersion) {
      return JSON.parse(activeVersion.document) as PolicyDocument;
    }

    return {
      apiVersion: policy.apiVersion as "policy.zenic.dev/v1",
      kind: "PolicyDocument" as const,
      metadata: {
        id: policy.policyId,
        name: policy.name,
        version: policy.version,
        description: policy.description,
        labels: JSON.parse(policy.labels) as Record<string, string>,
        compliance: JSON.parse(policy.compliance) as PolicyDocument["metadata"]["compliance"],
        author: policy.author ?? undefined,
        createdAt: policy.createdAt.toISOString(),
        updatedAt: policy.updatedAt.toISOString(),
      },
      statements: JSON.parse(policy.statements) as PolicyDocument["statements"],
      tests: JSON.parse(policy.tests) as PolicyDocument["tests"],
    };
  } catch {
    return null;
  }
}

/**
 * Generate a unique approval ID.
 */
function generateApprovalId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 10);
  return `apr_${ts}_${rand}`;
}

// ─── Public API Functions ─────────────────────────────────────────────

/**
 * Create a new approval request.
 *
 * 1. Validate proposed document
 * 2. Set initial status to "draft"
 * 3. Calculate required approvals based on policy risk
 * 4. Set expiry date (default 72 hours)
 * 5. Check auto-approve rules
 * 6. Persist to PolicyApproval table
 */
export async function createApprovalRequest(
  input: CreateApprovalRequestInput,
): Promise<PolicyApprovalRequest> {
  const {
    title,
    description,
    proposedDocument,
    priority = ApprovalPriorityEnum.MEDIUM,
    targetPolicyId,
    previousVersion,
    simulationId,
    requestedBy,
    requiredReviewerRoles,
    autoApproveRules,
    expiryHours = 72,
  } = input;

  validateProposedDocument(proposedDocument);

  const requiredApprovals = calculateRequiredApprovals(proposedDocument, priority);
  const reviewerRoles = requiredReviewerRoles ?? calculateRequiredReviewerRoles(proposedDocument, priority);
  const rules = autoApproveRules ?? [];
  const expiresAt = new Date(Date.now() + expiryHours * 60 * 60 * 1000);
  const approvalId = generateApprovalId();

  const record = await db.policyApproval.create({
    data: {
      approvalId,
      title,
      description,
      status: ApprovalStatusEnum.DRAFT,
      priority,
      targetPolicyId: targetPolicyId ?? null,
      previousVersion: previousVersion ?? null,
      proposedDocument: JSON.stringify(proposedDocument),
      simulationId: simulationId ?? null,
      requestedBy,
      requiredApprovals,
      currentApprovals: 0,
      approvals: "[]",
      requiredReviewerRoles: JSON.stringify(reviewerRoles),
      autoApproveRules: JSON.stringify(rules),
      autoApproved: false,
      expiresAt,
      deployedAt: null,
    },
  });

  return mapDbToApprovalRequest(record);
}
