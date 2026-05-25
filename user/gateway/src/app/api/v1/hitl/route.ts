// ─── Zenic-Agents v3 — HITL API: List + Create Approval Requests ──────
// GET  /api/v1/hitl          — List approval requests
// POST /api/v1/hitl          — Create an approval request
// ⚠️ SECURITY FIX (Phase 0): Added authentication to all endpoints

import { NextRequest, NextResponse } from "next/server";
import { getApprovalEngine } from "@/lib/hitl";
import { ApprovalRequestStatus, ApprovalPriority, ApprovalType } from "@/lib/hitl";
import { requireAuth, requireAuthAndPermission, handleAuthError } from "@/lib/auth";

// GET /api/v1/hitl
export async function GET(request: NextRequest) {
  try {
    const { user } = await requireAuth(request);

    const { searchParams } = new URL(request.url);
    const statusParam = searchParams.get("status");
    const priority = searchParams.get("priority") as ApprovalPriority | null;
    const requesterId = searchParams.get("requesterId");
    const type = searchParams.get("type") as ApprovalType | null;
    const targetResource = searchParams.get("targetResource");
    const page = Math.max(1, Number(searchParams.get("page")) || 1);
    const pageSize = Math.min(100, Math.max(1, Number(searchParams.get("pageSize")) || 20));
    const sortBy = (searchParams.get("sortBy") as "createdAt" | "updatedAt" | "priority" | "deadline") ?? "createdAt";
    const sortOrder = (searchParams.get("sortOrder") as "asc" | "desc") ?? "desc";

    // Parse status — can be comma-separated for multiple values
    let status: ApprovalRequestStatus | ApprovalRequestStatus[] | undefined;
    if (statusParam) {
      const statuses = statusParam.split(",");
      if (statuses.length === 1) {
        status = statuses[0] as ApprovalRequestStatus;
      } else {
        status = statuses as ApprovalRequestStatus[];
      }
    }

    const engine = getApprovalEngine();
    const result = await engine.listRequests({
      status,
      priority: priority ?? undefined,
      // SECURITY: If no specific requesterId filter, scope to authenticated user's tenant
      requesterId: requesterId ?? undefined,
      type: type ?? undefined,
      targetResource: targetResource ?? undefined,
      page,
      pageSize,
      sortBy,
      sortOrder,
    });

    return NextResponse.json({
      success: true,
      data: result.data,
      total: result.total,
      page: result.page,
      pageSize: result.pageSize,
      totalPages: Math.ceil(result.total / result.pageSize),
    });
  } catch (error) {
    const authResponse = handleAuthError(error);
    if (authResponse) return authResponse;

    console.error("[HITL GET]", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch approval requests", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}

// POST /api/v1/hitl
export async function POST(request: NextRequest) {
  try {
    // SECURITY: Require at least operator role to create approval requests
    const { user } = await requireAuthAndPermission(request, "operator");

    const body = await request.json();

    // Validate required fields
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

    const engine = getApprovalEngine();
    const result = await engine.createRequest({
      title: body.title,
      description: body.description,
      type: body.type,
      priority: body.priority,
      // SECURITY: Use authenticated user identity, not body values
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
    });

    return NextResponse.json({
      success: true,
      data: result,
    }, { status: 201 });
  } catch (error) {
    const authResponse = handleAuthError(error);
    if (authResponse) return authResponse;

    console.error("[HITL POST]", error);
    return NextResponse.json(
      { success: false, error: "Failed to create approval request", code: "INTERNAL_ERROR" },
      { status: 500 },
    );
  }
}
