import { db } from "@/lib/db";
import type { PolicyDocument, PolicyApprovalRequest, ApprovalDecision, AutoApproveRule } from "../types";
import { ApprovalStatus as ApprovalStatusEnum } from "../types/approval";
import { validateTransition } from "./types";
import { mapDbToApprovalRequest, loadExistingDocument, evaluateAutoApproveRules } from "./workflow";
import { createVersion } from "../versioning";
import { computeContentHash } from "../yaml-loader";

// ─── Internal: Create Approval Record in DB ───────────────────────────

async function createApprovalRecord(
  approvalId: string,
  targetPolicyId: string | null,
  previousVersion: string | null,
  proposedDocument: PolicyDocument,
  simulationId: string | null,
  requestedBy: string,
  requiredApprovals: number,
  reviewerRoles: string[],
  rules: AutoApproveRule[],
  expiresAt: Date | null,
): Promise<PolicyApprovalRequest> {
  const record = await db.policyApproval.create({
    data: {
      approvalId,
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

/**
 * Submit an approval request for review.
 * Moves from "draft" to "pending_review".
 * If auto-approve rules match → auto-approve immediately.
 */
export async function submitForReview(
  approvalId: string,
): Promise<PolicyApprovalRequest> {
  const record = await db.policyApproval.findUnique({
    where: { approvalId },
  });
  if (!record) {
    throw new Error(`Approval request "${approvalId}" not found`);
  }

  validateTransition(record.status, ApprovalStatusEnum.PENDING_REVIEW);

  if (!record.title || !record.proposedDocument || !record.requestedBy) {
    throw new Error("Cannot submit for review: missing required fields (title, proposedDocument, requestedBy)");
  }

  const proposedDocument = JSON.parse(record.proposedDocument) as PolicyDocument;
  const existingDocument = await loadExistingDocument(record.targetPolicyId);
  const autoApproveRules = JSON.parse(record.autoApproveRules) as AutoApproveRule[];

  const shouldAutoApprove = evaluateAutoApproveRules(autoApproveRules, proposedDocument, existingDocument);

  const newStatus = shouldAutoApprove
    ? ApprovalStatusEnum.APPROVED
    : ApprovalStatusEnum.PENDING_REVIEW;

  const updated = await db.policyApproval.update({
    where: { approvalId },
    data: {
      status: newStatus,
      autoApproved: shouldAutoApprove,
      currentApprovals: shouldAutoApprove
        ? record.requiredApprovals
        : record.currentApprovals,
      updatedAt: new Date(),
    },
  });

  return mapDbToApprovalRequest(updated);
}

/**
 * Add an approval or rejection decision to an approval request.
 */
export async function approveRequest(
  approvalId: string,
  decision: ApprovalDecision,
): Promise<PolicyApprovalRequest> {
  const record = await db.policyApproval.findUnique({
    where: { approvalId },
  });
  if (!record) {
    throw new Error(`Approval request "${approvalId}" not found`);
  }

  if (record.status !== ApprovalStatusEnum.PENDING_REVIEW) {
    throw new Error(
      `Cannot add decision to approval request in "${record.status}" status. ` +
      `Expected "${ApprovalStatusEnum.PENDING_REVIEW}".`
    );
  }

  const requiredRoles = JSON.parse(record.requiredReviewerRoles) as string[];
  if (requiredRoles.length > 0 && !requiredRoles.includes(decision.role)) {
    throw new Error(
      `Reviewer role "${decision.role}" is not authorized. ` +
      `Required roles: [${requiredRoles.join(", ")}]`
    );
  }

  const existingApprovals = JSON.parse(record.approvals) as ApprovalDecision[];
  const alreadyReviewed = existingApprovals.some((a) => a.reviewerId === decision.reviewerId);
  if (alreadyReviewed) {
    throw new Error(
      `Reviewer "${decision.reviewerId}" has already submitted a decision on this request.`
    );
  }

  const updatedApprovals = [...existingApprovals, decision];
  let newStatus = record.status;
  let newCurrentApprovals = record.currentApprovals;

  if (decision.decision === "rejected") {
    validateTransition(record.status, ApprovalStatusEnum.REJECTED);
    newStatus = ApprovalStatusEnum.REJECTED;
  } else {
    newCurrentApprovals = record.currentApprovals + 1;
    if (newCurrentApprovals >= record.requiredApprovals) {
      validateTransition(record.status, ApprovalStatusEnum.APPROVED);
      newStatus = ApprovalStatusEnum.APPROVED;
    }
  }

  const updated = await db.$transaction(async (tx) => {
    const freshRecord = await tx.policyApproval.findUnique({
      where: { approvalId },
    });
    if (!freshRecord) {
      throw new Error(`Approval request "${approvalId}" not found during transaction`);
    }

    if (freshRecord.status !== ApprovalStatusEnum.PENDING_REVIEW) {
      throw new Error(
        `Approval request "${approvalId}" status changed to "${freshRecord.status}" during review. Please retry.`
      );
    }

    const freshApprovals = JSON.parse(freshRecord.approvals) as ApprovalDecision[];
    const mergedApprovals = [...freshApprovals, decision];

    let finalStatus = freshRecord.status;
    let finalCurrentApprovals = freshRecord.currentApprovals;

    if (decision.decision === "rejected") {
      finalStatus = ApprovalStatusEnum.REJECTED;
    } else {
      finalCurrentApprovals = freshRecord.currentApprovals + 1;
      if (finalCurrentApprovals >= freshRecord.requiredApprovals) {
        finalStatus = ApprovalStatusEnum.APPROVED;
      }
    }

    return tx.policyApproval.update({
      where: { approvalId },
      data: {
        status: finalStatus,
        currentApprovals: finalCurrentApprovals,
        approvals: JSON.stringify(mergedApprovals),
        updatedAt: new Date(),
      },
    });
  });

  return mapDbToApprovalRequest(updated);
}

/**
 * Deploy an approved policy change.
 */
export async function deployApproval(
  approvalId: string,
): Promise<PolicyApprovalRequest> {
  const record = await db.policyApproval.findUnique({
    where: { approvalId },
  });
  if (!record) {
    throw new Error(`Approval request "${approvalId}" not found`);
  }

  validateTransition(record.status, ApprovalStatusEnum.DEPLOYED);

  const proposedDocument = JSON.parse(record.proposedDocument) as PolicyDocument;
  const policyId = record.targetPolicyId ?? proposedDocument.metadata.id;

  await createVersion({
    policyId,
    document: proposedDocument,
    changeDescription: record.description,
    createdBy: record.requestedBy,
  });

  const newContentHash = computeContentHash(proposedDocument);
  await db.declPolicy.update({
    where: { policyId },
    data: {
      contentHash: newContentHash,
      version: proposedDocument.metadata.version,
      statements: JSON.stringify(proposedDocument.statements),
      tests: JSON.stringify(proposedDocument.tests ?? []),
      labels: JSON.stringify(proposedDocument.metadata.labels ?? {}),
      compliance: JSON.stringify(proposedDocument.metadata.compliance ?? []),
      updatedAt: new Date(),
    },
  });

  const updated = await db.policyApproval.update({
    where: { approvalId },
    data: {
      status: ApprovalStatusEnum.DEPLOYED,
      deployedAt: new Date(),
      updatedAt: new Date(),
    },
  });

  return mapDbToApprovalRequest(updated);
}
