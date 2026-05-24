"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import { mutate } from 'swr';

/**
 * Sprint 7: Real-time event hook using Server-Sent Events.
 * Connects to /api/dashboard/stream and triggers SWR revalidation
 * when specific event types arrive, replacing the 15s polling approach.
 *
 * Exposes connection status for UI indicators.
 */

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export interface RealtimeEvent {
  type: 'connected' | 'metrics_update' | 'sna_alert' | 'pipeline_step' | 'activity_new' | 'heartbeat';
  timestamp: number;
  data?: unknown;
}

// Map event types to the SWR keys they should revalidate
const EVENT_SWR_KEYS: Record<string, string[]> = {
  metrics_update: ['/api/dashboard/metrics', '/api/dashboard/roi'],
  sna_alert: ['/api/dashboard/sna-alerts'],
  pipeline_step: ['/api/dashboard/pipeline-status'],
  activity_new: ['/api/dashboard/activity', '/api/dashboard/ledger'],
};

function handleEventMessage(event: MessageEvent) {
  try {
    const payload: RealtimeEvent = JSON.parse(event.data);
    const keys = EVENT_SWR_KEYS[payload.type];
    if (keys) {
      keys.forEach((key) => {
        mutate(key, undefined, { revalidate: true });
      });
    }
  } catch {
    // Ignore malformed events
  }
}

export function useRealtimeEvents(enabled = true) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  // Ref to hold the connect function so the timeout can call it without
  // hitting the "accessed before declaration" lint rule
  const connectRef = useRef<() => void>(() => {});
  const [status, setStatus] = useState<ConnectionStatus>('connecting');

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    const connect = () => {
      // Close existing
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      const es = new EventSource('/api/dashboard/stream');
      eventSourceRef.current = es;

      es.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setStatus('connected');
      };

      es.onmessage = handleEventMessage;

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        setStatus('disconnected');

        // Exponential backoff (max 30s)
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
        reconnectAttemptsRef.current += 1;

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          // Use ref to call the latest connect function
          connectRef.current();
        }, delay);
      };
    };

    // Store in ref for recursive reconnect
    connectRef.current = connect;

    // Initial connection
    connect();

    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [enabled]);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  const reconnect = useCallback(() => {
    connectRef.current();
  }, []);

  return {
    status,
    disconnect,
    reconnect,
  };
}
