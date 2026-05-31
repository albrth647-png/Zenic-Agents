// AG-UI Protocol — Event ingestion endpoint
// Receives AG-UI events from Python agents and broadcasts to connected clients

import { NextRequest, NextResponse } from "next/server";
import type { AGUIAnyEvent } from "@/lib/ag-ui/types";

// In-memory event store for MVP (will be Redis in production)
const eventStore: Map<string, AGUIAnyEvent[]> = new Map();

export async function POST(request: NextRequest) {
  try {
    const event: AGUIAnyEvent = await request.json();

    // Validate event structure
    if (!event.type || !event.agentId || !event.sessionId) {
      return NextResponse.json(
        { success: false, error: "Invalid AG-UI event: missing required fields" },
        { status: 400 }
      );
    }

    // Store event
    const sessionEvents = eventStore.get(event.sessionId) || [];
    sessionEvents.push(event);
    eventStore.set(event.sessionId, sessionEvents);

    return NextResponse.json({
      success: true,
      eventId: `${event.type}_${event.sessionId}_${event.timestamp}`,
      sessionId: event.sessionId,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to process AG-UI event" },
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

  const events = eventStore.get(sessionId) || [];
  return NextResponse.json({ success: true, events, total: events.length });
}
