// ─── Zenic-Agents v3 — HITL API: Coordinator Full Approve ────────────
// POST /api/v1/hitl/coordinator/approve
// ⚠️ SECURITY FIX (Phase 0): Added authentication — identity from verified session

import { NextRequest, NextResponse } from "next/server";
import { getHITLCoordinator } from "@/lib/hitl/hitl-coordinator/_coordinator";
import { requireAuthAndPermission, handleAuthError } from "@/lib/auth";

// POST /api/v1/hitl/coordinator/approve
export async function POST(request: NextRequest) {
  try {
    // SECURITY: Require operator+ role for coordinator approve
    const { user } = await requireAuthAndPermission(request, "operator");

    const body = await request.json();

    if (!body.requestId) {
      return NextResponse.json(
        { success: false, error: "Missing required field: requestId", code: "VALIDATION_ERROR" },
        { status: 400 },
      );
    }

    if (!body.reason || body.riskAcknowledgment === undefined || body.complianceCheck === undefined) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing justification fields: reason, riskAcknowledgment, complianceCheck",
          code: "VALIDATION_ERROR",
        },
        { status: 400 },
      );
    }

    const coordinator = getHITLCoordinator();
    const result = await coordinator.fullApprove(
      body.requestId,
      {
        // SECURITY: identity from verified session, NOT request body
        decisionBy: user.id,
        decisionByName: user.name || user.email,
        role: user.role,
        comment: body.comment,
        delegatedFrom: body.delegatedFrom,
      },
      {
        reason: body.reason,
        riskAcknowledgment: body.riskAcknowledgment,
        complianceCheck: body.complianceCheck,
        businessJustification: body.businessJustification,
        createdBy: user.id,
        createdByName: user.name || user.email,
        decisionId: body.decisionId,
      },
    );

    return NextResponse.json({
      success: true,
      data: result,
    });
  } catch (error) {
    const authResponse = handleAuthError(error);
    if (authResponse) return authResponse;

    if (error instanceof Error) {
      if (error.message.includes("not found")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "NOT_FOUND" },
          { status: 404 },
        );
      }
      if (error.message.includes("validation failed")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "VALIDATION_ERROR" },
          { status: 400 },
        );
      }
      if (error.message.includes("Cannot approve") || error.message.includes("already approved")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST coordinator/approve]", error);
    return NextResponse.json(
      { success: false, error: "Failed to approve request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
