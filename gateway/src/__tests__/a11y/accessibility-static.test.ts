// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Test riguroso — Accesibilidad (verificación estática)
// No renderizamos componentes que dependan de Next.js Router.
// En su lugar, verificamos que los atributos de accesibilidad están presentes
// en los archivos fuente.
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const srcDir = resolve(__dirname, '../../');

function readComponent(relPath: string): string {
  return readFileSync(resolve(srcDir, relPath), 'utf-8');
}

describe('Accesibilidad — verificación estática de atributos ARIA', () => {
  it('DashboardHeader tiene role="status" y aria-live="polite" en indicador SSE', () => {
    const source = readComponent('components/dashboard/DashboardHeader.tsx');
    expect(source).toContain('role="status"');
    expect(source).toContain('aria-live="polite"');
    expect(source).toContain('data-testid="sse-status"');
  });

  it('DashboardHeader tiene title en botón de tema', () => {
    const source = readComponent('components/dashboard/DashboardHeader.tsx');
    expect(source).toContain('title="Cambiar tema"');
  });

  it('DashboardSidebar tiene aria-label="Navegación principal"', () => {
    const source = readComponent('components/dashboard/DashboardSidebar.tsx');
    expect(source).toContain('aria-label="Navegación principal"');
  });

  it('DashboardSidebar tiene aria-expanded en secciones colapsables', () => {
    const source = readComponent('components/dashboard/DashboardSidebar.tsx');
    expect(source).toContain('aria-expanded');
  });

  it('DashboardSidebar tiene aria-current="page" en item activo', () => {
    const source = readComponent('components/dashboard/DashboardSidebar.tsx');
    expect(source).toContain('aria-current');
  });

  it('DashboardSidebar tiene role="status" en indicador "En línea"', () => {
    const source = readComponent('components/dashboard/DashboardSidebar.tsx');
    expect(source).toContain('role="status"');
  });

  it('DashboardSidebar tiene title en botón de cerrar sesión', () => {
    const source = readComponent('components/dashboard/DashboardSidebar.tsx');
    expect(source).toContain('title="Cerrar sesión"');
  });

  it('SidebarTrigger tiene sr-only text para lectores de pantalla', () => {
    const source = readComponent('components/ui/sidebar/_sidebar_footer.tsx');
    expect(source).toContain('sr-only');
    expect(source).toContain('Toggle Sidebar');
  });

  it('SidebarRail tiene aria-label', () => {
    const source = readComponent('components/ui/sidebar/_sidebar_footer.tsx');
    expect(source).toContain('aria-label="Toggle Sidebar"');
  });

  it('Todos los error.tsx tienen títulos accesibles', () => {
    const errorFiles = [
      'app/(dashboard)/dashboard/arbitraje/error.tsx',
      'app/(dashboard)/dashboard/boveda/error.tsx',
      'app/(dashboard)/dashboard/nichos/error.tsx',
      'app/(dashboard)/dashboard/apis/error.tsx',
      'app/(dashboard)/dashboard/policies/error.tsx',
      'app/(dashboard)/dashboard/integrations/error.tsx',
      'app/(dashboard)/dashboard/settings/error.tsx',
      'app/(dashboard)/dashboard/profile/error.tsx',
    ];

    errorFiles.forEach((file) => {
      const source = readComponent(file);
      // Cada error page debe tener un h2 o heading
      expect(source).toMatch(/<h[12]/);
      // Cada error page debe tener un botón de reintentar
      expect(source).toMatch(/Reintentar|retry/i);
    });
  });

  it('Todos los loading.tsx tienen indicadores visuales accesibles', () => {
    const loadingFiles = [
      'app/(dashboard)/dashboard/arbitraje/loading.tsx',
      'app/(dashboard)/dashboard/boveda/loading.tsx',
      'app/(dashboard)/dashboard/nichos/loading.tsx',
      'app/(dashboard)/dashboard/apis/loading.tsx',
      'app/(dashboard)/dashboard/policies/loading.tsx',
      'app/(dashboard)/dashboard/integrations/loading.tsx',
      'app/(dashboard)/dashboard/settings/loading.tsx',
      'app/(dashboard)/dashboard/profile/loading.tsx',
    ];

    loadingFiles.forEach((file) => {
      const source = readComponent(file);
      // Cada loading page debe tener texto descriptivo
      expect(source).toMatch(/Cargando|Loading/i);
    });
  });
});
