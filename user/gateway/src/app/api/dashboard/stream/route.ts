import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * Sprint 7: Server-Sent Events endpoint for real-time dashboard updates.
 * Pushes event types: metrics_update, sna_alert, pipeline_step, activity_new
 * Uses a simple heartbeat approach — SSE triggers SWR revalidation on the client.
 * The actual data fetching happens via SWR, so this endpoint only signals
 * that new data is available, keeping the connection lightweight.
 */
export async function GET(request: NextRequest) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      // Send initial connection event
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ type: 'connected', timestamp: Date.now() })}\n\n`)
      );

      // Keep-alive: send heartbeat every 30s
      const heartbeat = setInterval(() => {
        try {
          controller.enqueue(
            encoder.encode(`:heartbeat\n\n`)
          );
        } catch {
          clearInterval(heartbeat);
        }
      }, 30000);

      // Clean up on close
      request.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        try { controller.close(); } catch { /* stream already closed */ }
      });
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
