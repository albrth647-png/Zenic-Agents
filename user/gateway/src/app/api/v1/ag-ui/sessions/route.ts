// AG-UI Protocol — Session management

import { NextRequest, NextResponse } from "next/server";
import type { AGUISession } from "@/lib/ag-ui/types";

const sessions: Map<string, AGUISession> = new Map();

export async function POST(request: NextRequest) {
  try {
    const { agentId } = (await request.json()) as { agentId: string };

    if (!agentId) {
      return NextResponse.json(
        { success: false, error: "agentId is required" },
        { status: 400 }
      );
    }

    const sessionId = `agui_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    const session: AGUISession = {
      sessionId,
      agentId,
      createdAt: Date.now(),
      lastEventAt: Date.now(),
      components: new Map(),
      status: "active",
    };

    sessions.set(sessionId, session);

    return NextResponse.json({ success: true, sessionId, agentId });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to create AG-UI session" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const sessionId = searchParams.get("sessionId");

  if (sessionId) {
    const session = sessions.get(sessionId);
    if (!session) {
      return NextResponse.json(
        { success: false, error: "Session not found" },
        { status: 404 }
      );
    }
    return NextResponse.json({ success: true, session });
  }

  // List all sessions
  const allSessions = Array.from(sessions.values()).map((s) => ({
    sessionId: s.sessionId,
    agentId: s.agentId,
    createdAt: s.createdAt,
    lastEventAt: s.lastEventAt,
    status: s.status,
    componentCount: s.components.size,
  }));

  return NextResponse.json({ success: true, sessions: allSessions, total: allSessions.length });
}
