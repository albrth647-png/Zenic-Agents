// ─── Zenic-Agents v3 — HITL API: Coordinator Full Reject ─────────────
// POST /api/v1/hitl/coordinator/reject
// ⚠️ SECURITY FIX (Phase 0): Added authentication — identity from verified session

import { NextRequest, NextResponse } from "next/server";
import { getHITLCoordinator } from "@/lib/hitl";
import { requireAuthAndPermission, handleAuthError } from "@/lib/auth";

// POST /api/v1/hitl/coordinator/reject
export async function POST(request: NextRequest) {
  try {
    // SECURITY: Require operator+ role for coordinator reject
    const { user } = await requireAuthAndPermission(request, "operator");

    const body = await request.json();

    if (!body.requestId) {
      return NextResponse.json(
        { success: false, error: "Missing required field: requestId", code: "VALIDATION_ERROR" },
        { status: 400 },
      );
    }

    if (!body.comment) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing required field: comment (rejection reason is required)",
          code: "VALIDATION_ERROR",
        },
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
    const result = await coordinator.fullReject(
      body.requestId,
      {
        // SECURITY: identity from verified session
        decisionBy: user.id,
        decisionByName: user.name || user.email,
        role: user.role,
        comment: body.comment,
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
      if (error.message.includes("Cannot reject")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST coordinator/reject]", error);
    return NextResponse.json(
      { success: false, error: "Failed to reject request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
