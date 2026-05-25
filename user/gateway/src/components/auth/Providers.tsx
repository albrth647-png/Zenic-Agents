"use client";

import { SessionProvider } from "next-auth/react";
import { SWRConfig } from "swr";
import { defaultSWRConfig } from "@/lib/swr-config";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <SWRConfig value={defaultSWRConfig}>
        {children}
      </SWRConfig>
    </SessionProvider>
  );
}

export default Providers;
