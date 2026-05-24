import { test, expect } from '@playwright/test';

test.describe('Dashboard Smoke Tests', () => {
  test('rutas del dashboard están protegidas', async ({ page }) => {
    // All dashboard routes should redirect to login when not authenticated
    const routes = [
      '/dashboard',
      '/dashboard/arbitraje',
      '/dashboard/boveda',
      '/dashboard/nichos',
      '/dashboard/apis',
      '/dashboard/policies',
      '/dashboard/integrations',
      '/dashboard/settings',
      '/dashboard/profile',
    ];

    for (const route of routes) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 5000 });
    }
  });

  test('página 404 funciona', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page.locator('text=Ruta no encontrada')).toBeVisible();
  });

  test('endpoint de salud responde', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
  });
});
