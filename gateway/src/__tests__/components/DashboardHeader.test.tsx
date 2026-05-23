// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Test riguroso — DashboardHeader con providers reales
// Sin mocks. Renderiza el componente real con providers reales.
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SWRConfig } from 'swr';
import { SessionProvider } from 'next-auth/react';
import { ThemeProvider } from 'next-themes';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { SidebarProvider } from '@/components/ui/sidebar';
import { RealtimeProvider } from '@/components/dashboard/RealtimeProvider';

// Sesión real para el test
const sessionReal = {
  user: { name: 'Admin Test', email: 'admin@zenic.dev' },
  expires: '2099-01-01',
};

function TestWrapper({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider session={sessionReal}>
      <SWRConfig value={{ dedupingInterval: 0, provider: () => new Map() }}>
        <ThemeProvider attribute="class" defaultTheme="dark">
          <SidebarProvider>
            <RealtimeProvider>
              {children}
            </RealtimeProvider>
          </SidebarProvider>
        </ThemeProvider>
      </SWRConfig>
    </SessionProvider>
  );
}

describe('DashboardHeader', () => {
  it('renderiza el título de la ruta /dashboard', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    // El título incluye "Centro de Comando" para /dashboard (mocked by usePathname)
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toBeTruthy();
    expect(heading.textContent).toContain('Zenic');
  });

  it('muestra indicador de conexión SSE', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    // Debe haber un indicador de estado (En vivo / Conectando / Sin conexión)
    const statusIndicator = screen.getByTestId('sse-status');
    expect(statusIndicator).toBeTruthy();
  });

  it('tiene botón de cambiar tema', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    const themeBtn = screen.getByTitle('Cambiar tema');
    expect(themeBtn).toBeTruthy();
  });

  it('tiene botón de actualizar', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    const refreshBtn = screen.getByText('Actualizar');
    expect(refreshBtn).toBeTruthy();
  });

  it('tiene SidebarTrigger', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    // SidebarTrigger should render a button
    const sidebarTrigger = document.querySelector('[data-sidebar="trigger"]');
    expect(sidebarTrigger).toBeTruthy();
  });

  it('muestra badge de tier', () => {
    render(<DashboardHeader />, { wrapper: TestWrapper });
    // Tier badge — puede ser Starter, Business, Enterprise, etc.
    const badge = document.querySelector('[data-testid="tier-badge"]') || 
      screen.getByText(/Starter|Business|Enterprise|On-Premise|Trial/);
    expect(badge).toBeTruthy();
  });
});
