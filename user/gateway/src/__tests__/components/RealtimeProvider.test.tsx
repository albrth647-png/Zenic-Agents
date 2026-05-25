// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Test riguroso — RealtimeProvider con contexto real
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { SessionProvider } from 'next-auth/react';
import { RealtimeProvider, useRealtimeStatus } from '@/components/dashboard/RealtimeProvider';
import type { ReactNode } from 'react';

const sessionReal = {
  user: { name: 'Admin Test', email: 'admin@zenic.dev' },
  expires: '2099-01-01',
};

function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <SessionProvider session={sessionReal}>
      <SWRConfig value={{ dedupingInterval: 0, provider: () => new Map() }}>
        <RealtimeProvider>
          {children}
        </RealtimeProvider>
      </SWRConfig>
    </SessionProvider>
  );
}

describe('RealtimeProvider', () => {
  it('useRealtimeStatus devuelve un estado válido dentro del provider', () => {
    const { result } = renderHook(() => useRealtimeStatus(), {
      wrapper: TestWrapper,
    });

    const status = result.current;
    expect(['connected', 'connecting', 'disconnected']).toContain(status);
  });

  it('useRealtimeStatus fuera del provider devuelve "connecting" (default)', () => {
    const { result } = renderHook(() => useRealtimeStatus());
    expect(result.current).toBe('connecting');
  });
});
