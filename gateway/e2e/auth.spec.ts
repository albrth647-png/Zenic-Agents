// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: E2E — Auth flow smoke tests
// Sin mocks. Prueba contra el servidor real.
// ═══════════════════════════════════════════════════════════════════════════════

import { test, expect } from '@playwright/test';

test.describe('Autenticación', () => {
  test('redirige usuarios no autenticados a login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10000 });
  });

  test('página de login renderiza campos de email y password', async ({ page }) => {
    await page.goto('/auth/login');
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible({ timeout: 5000 });
  });

  test('página de registro renderiza campos requeridos', async ({ page }) => {
    await page.goto('/auth/register');
    const nameInput = page.locator('input[name="name"]');
    await expect(nameInput).toBeVisible({ timeout: 5000 });
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await expect(emailInput).toBeVisible({ timeout: 5000 });
  });

  test('página de recuperar contraseña renderiza campo de email', async ({ page }) => {
    await page.goto('/auth/forgot-password');
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await expect(emailInput).toBeVisible({ timeout: 5000 });
  });

  test('login muestra error con credenciales inválidas', async ({ page }) => {
    await page.goto('/auth/login');
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await emailInput.fill('invalid@test.com');
    const passwordInput = page.locator('input[type="password"]');
    await passwordInput.fill('wrongpassword123');
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();
    // Debe mostrar algún tipo de mensaje de error o quedarse en login
    await expect(page).toHaveURL(/\/auth/, { timeout: 5000 });
  });
});

test.describe('Rutas protegidas', () => {
  const rutasProtegidas = [
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

  for (const ruta of rutasProtegidas) {
    test(`${ruta} redirige a login sin auth`, async ({ page }) => {
      await page.goto(ruta);
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10000 });
    });
  }
});

test.describe('Páginas públicas', () => {
  test('404 muestra "Ruta no encontrada"', async ({ page }) => {
    await page.goto('/esta-ruta-no-existe');
    await expect(page.locator('text=Ruta no encontrada')).toBeVisible({ timeout: 5000 });
  });

  test('health endpoint responde', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
  });
});
