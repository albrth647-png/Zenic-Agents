// ─── Zenic-Agents v3 — HITL API: Reject Request ──────────────────────
// POST /api/v1/hitl/[requestId]/reject
// ⚠️ SECURITY FIX (Phase 0): Added authentication — decisionBy comes from verified session

import { NextRequest, NextResponse } from "next/server";
import { getApprovalEngine } from "@/lib/hitl/approval-engine/_engine";
import { requireAuthAndPermission, handleAuthError } from "@/lib/auth";

interface RouteParams {
  params: Promise<{ requestId: string }>;
}

// POST /api/v1/hitl/[requestId]/reject
export async function POST(
  request: NextRequest,
  { params }: RouteParams,
) {
  try {
    // SECURITY: Require operator+ role to reject requests
    const { user } = await requireAuthAndPermission(request, "operator");

    const { requestId } = await params;
    const body = await request.json();

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

    // SECURITY: decisionBy and role from verified session
    const engine = getApprovalEngine();
    const result = await engine.rejectRequest(requestId, {
      decisionBy: user.id,
      decisionByName: user.name || user.email,
      role: user.role,
      comment: body.comment,
    });

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
      if (error.message.includes("Cannot reject")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST reject]", error);
    return NextResponse.json(
      { success: false, error: "Failed to reject request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
