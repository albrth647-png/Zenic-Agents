// ─── Zenic-Agents v3 — HITL API: Coordinator Create Full Request ──────
// POST /api/v1/hitl/coordinator/create
// ⚠️ SECURITY FIX (Phase 0): Added authentication — requesterId from verified session

import { NextRequest, NextResponse } from "next/server";
import { getHITLCoordinator } from "@/lib/hitl";
import { requireAuthAndPermission, handleAuthError } from "@/lib/auth";

// POST /api/v1/hitl/coordinator/create
export async function POST(request: NextRequest) {
  try {
    // SECURITY: Require operator+ role for coordinator create
    const { user } = await requireAuthAndPermission(request, "operator");

    const body = await request.json();

    // Validate required fields for the base request
    if (!body.title || !body.description || !body.type || !body.targetResource || !body.targetAction) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing required fields: title, description, type, targetResource, targetAction",
          code: "VALIDATION_ERROR",
        },
        { status: 400 },
      );
    }

    // Validate type
    const validTypes: string[] = ["action_approval", "policy_change", "deployment", "data_access", "configuration", "financial", "security"];
    if (!validTypes.includes(body.type)) {
      return NextResponse.json(
        { success: false, error: `Invalid type. Must be one of: ${validTypes.join(", ")}`, code: "VALIDATION_ERROR" },
        { status: 400 },
      );
    }

    // Validate priority if provided
    if (body.priority) {
      const validPriorities: string[] = ["low", "medium", "high", "critical", "emergency"];
      if (!validPriorities.includes(body.priority)) {
        return NextResponse.json(
          { success: false, error: `Invalid priority. Must be one of: ${validPriorities.join(", ")}`, code: "VALIDATION_ERROR" },
          { status: 400 },
        );
      }
    }

    // Validate justification if provided
    if (body.justification) {
      if (!body.justification.reason || body.justification.riskAcknowledgment === undefined || body.justification.complianceCheck === undefined) {
        return NextResponse.json(
          {
            success: false,
            error: "Justification requires: reason, riskAcknowledgment, complianceCheck",
            code: "VALIDATION_ERROR",
          },
          { status: 400 },
        );
      }
    }

    const coordinator = getHITLCoordinator();
    const result = await coordinator.createFullRequest({
      title: body.title,
      description: body.description,
      type: body.type,
      priority: body.priority,
      // SECURITY: Use authenticated user identity
      requesterId: body.requesterId || user.id,
      requesterName: body.requesterName || user.name || user.email,
      targetResource: body.targetResource,
      targetAction: body.targetAction,
      actionPayload: body.actionPayload,
      undoPayload: body.undoPayload,
      isReversible: body.isReversible,
      undoWindowMs: body.undoWindowMs,
      deadline: body.deadline,
      requiredApprovals: body.requiredApprovals,
      approvalPolicy: body.approvalPolicy,
      parentId: body.parentId,
      tags: body.tags,
      metadata: body.metadata,
      evidence: body.evidence,
      justification: body.justification ? {
        ...body.justification,
        createdBy: body.justification.createdBy || user.id,
        createdByName: body.justification.createdByName || user.name || user.email,
      } : body.justification,
      autoRevertOnExpiry: body.autoRevertOnExpiry,
      revertAction: body.revertAction,
      expiryNotificationSchedule: body.expiryNotificationSchedule,
    });

    return NextResponse.json({
      success: true,
      data: result,
    }, { status: 201 });
  } catch (error) {
    const authResponse = handleAuthError(error);
    if (authResponse) return authResponse;

    if (error instanceof Error) {
      if (error.message.includes("validation failed")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "VALIDATION_ERROR" },
          { status: 400 },
        );
      }
    }
    console.error("[HITL POST coordinator/create]", error);
    return NextResponse.json(
      { success: false, error: "Failed to create full approval request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
