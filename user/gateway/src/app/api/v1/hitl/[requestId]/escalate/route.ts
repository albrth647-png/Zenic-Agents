// ─── Zenic-Agents v3 — HITL API: Escalate Request ────────────────────
// POST /api/v1/hitl/[requestId]/escalate
// ⚠️ SECURITY FIX (Phase 0): Added authentication — fromUserId from verified session

import { NextRequest, NextResponse } from "next/server";
import { getEscalationService } from "@/lib/hitl/delegation/_rules";
import { requireAuth, handleAuthError } from "@/lib/auth";

interface RouteParams {
  params: Promise<{ requestId: string }>;
}

// POST /api/v1/hitl/[requestId]/escalate
export async function POST(
  request: NextRequest,
  { params }: RouteParams,
) {
  try {
    // SECURITY: Require authentication — any authenticated user can escalate
    const { user } = await requireAuth(request);

    const { requestId } = await params;
    const body = await request.json();

    if (!body.toRole) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing required field: toRole",
          code: "VALIDATION_ERROR",
        },
        { status: 400 },
      );
    }

    const service = getEscalationService();
    const result = await service.escalateRequest(requestId, {
      // SECURITY: fromUserId from verified session, not request body
      fromUserId: body.fromUserId || user.id,
      toUserId: body.toUserId,
      toRole: body.toRole,
      reason: body.reason,
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
      if (error.message.includes("Cannot escalate") || error.message.includes("Maximum escalation")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST escalate]", error);
    return NextResponse.json(
      { success: false, error: "Failed to escalate request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
