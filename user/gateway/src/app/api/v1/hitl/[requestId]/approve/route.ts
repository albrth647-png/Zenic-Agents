// ─── Zenic-Agents v3 — HITL API: Approve Request ─────────────────────
// POST /api/v1/hitl/[requestId]/approve
// ⚠️ SECURITY FIX (Phase 0): Added authentication — decisionBy comes from verified session

import { NextRequest, NextResponse } from "next/server";
import { getApprovalEngine } from "@/lib/hitl/approval-engine/_engine";
import { requireAuthAndPermission, handleAuthError } from "@/lib/auth";

interface RouteParams {
  params: Promise<{ requestId: string }>;
}

// POST /api/v1/hitl/[requestId]/approve
export async function POST(
  request: NextRequest,
  { params }: RouteParams,
) {
  try {
    // SECURITY: Require operator+ role to approve requests
    const { user } = await requireAuthAndPermission(request, "operator");

    const { requestId } = await params;
    const body = await request.json();

    // SECURITY: decisionBy and role are taken from the verified session,
    // NOT from the request body. This prevents identity spoofing.
    const engine = getApprovalEngine();
    const result = await engine.approveRequest(requestId, {
      decisionBy: user.id,
      decisionByName: user.name || user.email,
      role: user.role,
      comment: body.comment,
      delegatedFrom: body.delegatedFrom,
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
      if (error.message.includes("Cannot approve") || error.message.includes("already approved")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST approve]", error);
    return NextResponse.json(
      { success: false, error: "Failed to approve request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
