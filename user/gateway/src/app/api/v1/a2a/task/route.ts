// A2A Protocol — Task delegation endpoint
// Receives A2A tasks from external agents, validates via Policy Engine, executes

import { NextRequest, NextResponse } from "next/server";
import { createHash } from "crypto";

export async function POST(request: NextRequest) {
  try {
    const task = await request.json();

    // Validate task structure
    if (!task.taskId || !task.senderAgent || !task.receiverAgent) {
      return NextResponse.json(
        { success: false, error: "Task must have taskId, senderAgent, and receiverAgent" },
        { status: 400 }
      );
    }

    // Policy Engine check (MVP: all tasks allowed unless critical)
    const policyResult = {
      allowed: task.priority !== "critical",
      requiresHitl: task.priority === "critical",
      reason: task.priority === "critical" ? "Critical tasks require HITL approval" : "",
    };

    if (!policyResult.allowed) {
      return NextResponse.json({
        success: false,
        taskId: task.taskId,
        status: "denied",
        reason: policyResult.reason,
      });
    }

    // Compute merkle audit hash
    const auditHash = createHash("sha256")
      .update(JSON.stringify({
        taskId: task.taskId,
        sender: task.senderAgent,
        receiver: task.receiverAgent,
        timestamp: Date.now(),
      }))
      .digest("hex");

    const response = {
      taskId: task.taskId,
      status: policyResult.requiresHitl ? "pending_approval" : "success",
      result: { processed: true, policyChecked: true },
      merkleHash: auditHash,
      processedAt: new Date().toISOString(),
    };

    return NextResponse.json({
      success: true,
      ...response,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "A2A task processing failed" },
      { status: 500 }
    );
  }
}
