// ─── Zenic-Agents v3 — HITL API: Delegate Request ────────────────────
// POST /api/v1/hitl/[requestId]/delegate
// ⚠️ SECURITY FIX (Phase 0): Added authentication — fromUserId from verified session

import { NextRequest, NextResponse } from "next/server";
import { getDelegationService } from "@/lib/hitl";
import { requireAuth, handleAuthError } from "@/lib/auth";

interface RouteParams {
  params: Promise<{ requestId: string }>;
}

// POST /api/v1/hitl/[requestId]/delegate
export async function POST(
  request: NextRequest,
  { params }: RouteParams,
) {
  try {
    // SECURITY: Require authentication for delegation
    const { user } = await requireAuth(request);

    const { requestId } = await params;
    const body = await request.json();

    if (!body.toUserId || !body.toUserName) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing required fields: toUserId, toUserName",
          code: "VALIDATION_ERROR",
        },
        { status: 400 },
      );
    }

    const service = getDelegationService();
    const result = await service.delegateRequest(requestId, {
      // SECURITY: fromUserId and fromUserName from verified session
      fromUserId: user.id,
      fromUserName: user.name || user.email,
      toUserId: body.toUserId,
      toUserName: body.toUserName,
      reason: body.reason,
      expiresAt: body.expiresAt,
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
      if (error.message.includes("Cannot delegate") || error.message.includes("yourself") || error.message.includes("depth") || error.message.includes("already has")) {
        return NextResponse.json(
          { success: false, error: error.message, code: "CONFLICT" },
          { status: 409 },
        );
      }
    }
    console.error("[HITL POST delegate]", error);
    return NextResponse.json(
      { success: false, error: "Failed to delegate request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
