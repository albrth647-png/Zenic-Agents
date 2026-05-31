// AG-UI Protocol — Component rendering endpoint
// Returns rendered component specs for a session

import { NextRequest, NextResponse } from "next/server";
import type { AGUIComponent, AGUIRenderEvent } from "@/lib/ag-ui/types";

// Shared store reference (in production, use Redis)
const componentStore: Map<string, AGUIComponent[]> = new Map();

export async function POST(request: NextRequest) {
  try {
    const { sessionId, agentId, components } = (await request.json()) as {
      sessionId: string;
      agentId: string;
      components: AGUIComponent[];
    };

    if (!sessionId || !agentId || !Array.isArray(components)) {
      return NextResponse.json(
        { success: false, error: "Missing required fields: sessionId, agentId, components" },
        { status: 400 }
      );
    }

    // Store components for this session
    const existing = componentStore.get(sessionId) || [];
    const updated = [...existing, ...components];
    componentStore.set(sessionId, updated);

    const _renderEvent: AGUIRenderEvent = {
      type: "render",
      agentId,
      sessionId,
      timestamp: Date.now(),
      components,
    };

    return NextResponse.json({
      success: true,
      renderedComponents: components.length,
      sessionId,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to render AG-UI components" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const sessionId = searchParams.get("sessionId");

  if (!sessionId) {
    return NextResponse.json(
      { success: false, error: "sessionId is required" },
      { status: 400 }
    );
  }

  const components = componentStore.get(sessionId) || [];
  return NextResponse.json({ success: true, components, total: components.length });
}
