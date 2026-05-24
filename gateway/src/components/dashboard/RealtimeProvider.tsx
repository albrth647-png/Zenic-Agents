"use client";

import { useRealtimeEvents } from "@/hooks/useRealtimeEvents";
import { createContext, useContext } from "react";
import type { ConnectionStatus } from "@/hooks/useRealtimeEvents";

// Expose connection status via context so DashboardHeader can read it
const RealtimeStatusContext = createContext<ConnectionStatus>("connecting");

export function useRealtimeStatus() {
  return useContext(RealtimeStatusContext);
}

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  // Connect to SSE when inside dashboard layout
  const { status } = useRealtimeEvents(true);

  return (
    <RealtimeStatusContext.Provider value={status}>
      {children}
    </RealtimeStatusContext.Provider>
  );
}
