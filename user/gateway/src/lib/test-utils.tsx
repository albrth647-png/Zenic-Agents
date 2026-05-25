import { render, type RenderOptions } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { SessionProvider } from 'next-auth/react';
import { SidebarProvider } from '@/components/ui/sidebar';
import type { ReactElement, ReactNode } from 'react';

/** Custom render that wraps components with all necessary providers */
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <SessionProvider session={{
        user: { name: 'Test User', email: 'test@zenic.dev' },
        expires: '2099-01-01',
      }}>
        <SWRConfig value={{ dedupingInterval: 0, provider: () => new Map() }}>
          <SidebarProvider>
            {children}
          </SidebarProvider>
        </SWRConfig>
      </SessionProvider>
    ),
    ...options,
  });
}

export { customRender as render };
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
