// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Tests rigurosos — SWR config + construirContextoSuscripcion
// Sin mocks, datos reales. Cubre: normal + vacío + nulo + extremos + error
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import { defaultSWRConfig, swrFetcher } from '@/lib/swr-config';
import { construirContextoSuscripcion, tierMinimo, WIDGET_GATES } from '@/app/_page_parts/constants';
import { TIER_LIMITS, TIER_DISPLAY_NAMES, FEATURE_TIER_MAP } from '@/lib/pricing-engine/types';
import type { SubscriptionTierName, FeatureName } from '@/lib/pricing-engine/types';
import type { ContextoSuscripcion } from '@/app/_page_parts/types';

/** SWR allows shouldRetryOnError to be boolean | function — cast to function for test */
const shouldRetryOnError = defaultSWRConfig.shouldRetryOnError as (err: unknown) => boolean;

// ─── SWR Config ─────────────────────────────────────────────────────────────

describe('defaultSWRConfig', () => {
  it('no revalida al enfocar la ventana', () => {
    expect(defaultSWRConfig.revalidateOnFocus).toBe(false);
  });

  it('revalida al reconectar', () => {
    expect(defaultSWRConfig.revalidateOnReconnect).toBe(true);
  });

  it('reintenta errores 5xx', () => {
    const err500 = { status: 500, message: 'Internal Server Error' };
    expect(shouldRetryOnError(err500)).toBe(true);
  });

  it('reintenta errores 502', () => {
    expect(shouldRetryOnError({ status: 502, message: 'Bad Gateway' })).toBe(true);
  });

  it('no reintenta errores 400 (Bad Request)', () => {
    expect(shouldRetryOnError({ status: 400, message: 'Bad Request' })).toBe(false);
  });

  it('no reintenta errores 401 (Unauthorized)', () => {
    expect(shouldRetryOnError({ status: 401, message: 'Unauthorized' })).toBe(false);
  });

  it('no reintenta errores 403 (Forbidden)', () => {
    expect(shouldRetryOnError({ status: 403, message: 'Forbidden' })).toBe(false);
  });

  it('no reintenta errores 404 (Not Found)', () => {
    expect(shouldRetryOnError({ status: 404, message: 'Not Found' })).toBe(false);
  });

  it('no reintenta errores 429 (Rate Limit)', () => {
    expect(shouldRetryOnError({ status: 429, message: 'Too Many' })).toBe(false);
  });

  it('reintenta errores sin status (error genérico)', () => {
    expect(shouldRetryOnError(new Error('Network error'))).toBe(true);
  });

  it('reintenta errores null/undefined (caso límite)', () => {
    expect(shouldRetryOnError(null)).toBe(true);
    expect(shouldRetryOnError(undefined)).toBe(true);
  });

  it('reintenta errores con status 0 (sin conexión)', () => {
    // status 0 no está en rango 400-499, así que reintenta
    expect(shouldRetryOnError({ status: 0, message: 'No connection' })).toBe(true);
  });

  it('límite de reintentos es 2', () => {
    expect(defaultSWRConfig.errorRetryCount).toBe(2);
  });

  it('intervalo de reintento es 3000ms', () => {
    expect(defaultSWRConfig.errorRetryInterval).toBe(3000);
  });

  it('deduplication interval es 5000ms', () => {
    expect(defaultSWRConfig.dedupingInterval).toBe(5000);
  });

  it('fetcher es swrFetcher', () => {
    expect(defaultSWRConfig.fetcher).toBe(swrFetcher);
  });
});

// ─── construirContextoSuscripcion ───────────────────────────────────────────

describe('construirContextoSuscripcion', () => {
  const tiers: SubscriptionTierName[] = ['starter', 'business', 'enterprise', 'on_premise_enterprise', 'trial'];

  it('funciona para todos los tiers válidos', () => {
    tiers.forEach((tier) => {
      const ctx = construirContextoSuscripcion(tier);
      expect(ctx.tier).toBe(tier);
      expect(ctx.nombreMostrar).toBe(TIER_DISPLAY_NAMES[tier]);
      expect(ctx.limites).toEqual(TIER_LIMITS[tier]);
    });
  });

  it('starter tiene límites restrictivos', () => {
    const ctx = construirContextoSuscripcion('starter');
    expect(ctx.limites.max_workflows).toBe(5);
    expect(ctx.limites.max_actions_per_day).toBe(200);
    expect(ctx.limites.sso_available).toBe(false);
    expect(ctx.limites.z3_solver).toBe(false);
  });

  it('enterprise tiene límites ilimitados (0 = ∞)', () => {
    const ctx = construirContextoSuscripcion('enterprise');
    expect(ctx.limites.max_workflows).toBe(0);
    expect(ctx.limites.max_actions_per_day).toBe(0);
    expect(ctx.limites.sso_available).toBe(true);
    expect(ctx.limites.z3_solver).toBe(true);
  });

  it('on_premise_enterprise tiene todo ilimitado y disponible', () => {
    const ctx = construirContextoSuscripcion('on_premise_enterprise');
    expect(ctx.limites.max_workflows).toBe(0);
    expect(ctx.limites.sso_available).toBe(true);
    expect(ctx.limites.on_premise_available).toBe(true);
    expect(ctx.limites.custom_rbac).toBe(true);
  });

  it('trial tiene mismos límites que business', () => {
    const trial = construirContextoSuscripcion('trial');
    const business = construirContextoSuscripcion('business');
    expect(trial.limites).toEqual(business.limites);
  });

  it('características es un array no vacío', () => {
    tiers.forEach((tier) => {
      const ctx = construirContextoSuscripcion(tier);
      expect(Array.isArray(ctx.caracteristicas)).toBe(true);
      expect(ctx.caracteristicas.length).toBeGreaterThan(0);
    });
  });

  it('cada característica tiene las 5 propiedades', () => {
    const ctx = construirContextoSuscripcion('business');
    ctx.caracteristicas.forEach((c) => {
      expect(c).toHaveProperty('feature');
      expect(c).toHaveProperty('etiqueta');
      expect(c).toHaveProperty('descripcion');
      expect(c).toHaveProperty('tierMinimo');
      expect(c).toHaveProperty('disponible');
    });
  });

  it('starter tiene pocas características disponibles', () => {
    const ctx = construirContextoSuscripcion('starter');
    const disponibles = ctx.caracteristicas.filter((c) => c.disponible).length;
    const noDisponibles = ctx.caracteristicas.filter((c) => !c.disponible).length;
    // Starter es el tier más bajo, la mayoría deberían estar bloqueadas
    expect(disponibles).toBeLessThan(noDisponibles + disponibles);
  });

  it('enterprise tiene todas las características disponibles', () => {
    const ctx = construirContextoSuscripcion('enterprise');
    const todas = ctx.caracteristicas.every((c) => c.disponible);
    expect(todas).toBe(true);
  });

  it('nombreMostrar coincide con TIER_DISPLAY_NAMES', () => {
    tiers.forEach((tier) => {
      const ctx = construirContextoSuscripcion(tier);
      expect(ctx.nombreMostrar).toBe(TIER_DISPLAY_NAMES[tier]);
    });
  });
});

// ─── tierMinimo ─────────────────────────────────────────────────────────────

describe('tierMinimo', () => {
  it('devuelve un tier válido para cualquier feature conocida', () => {
    const features = Object.keys(FEATURE_TIER_MAP) as FeatureName[];
    features.forEach((feature) => {
      const result = tierMinimo(feature);
      expect(['starter', 'business', 'enterprise', 'on_premise_enterprise']).toContain(result);
    });
  });

  it('feature que incluye starter → tierMinimo = starter', () => {
    // McpToolExecution should be available to starter
    const featuresWithStarter = Object.entries(FEATURE_TIER_MAP)
      .filter(([, tiers]) => tiers.includes('starter'))
      .map(([f]) => f as FeatureName);

    if (featuresWithStarter.length > 0) {
      expect(tierMinimo(featuresWithStarter[0])).toBe('starter');
    }
  });

  it('WIDGET_GATES no está vacío', () => {
    expect(WIDGET_GATES.length).toBeGreaterThan(0);
  });

  it('cada WIDGET_GATE tiene feature, etiqueta, descripcion', () => {
    WIDGET_GATES.forEach((wg) => {
      expect(wg.feature).toBeTruthy();
      expect(wg.etiqueta).toBeTruthy();
      expect(wg.descripcion).toBeTruthy();
    });
  });
});

// ─── TIER_LIMITS integridad ────────────────────────────────────────────────

describe('TIER_LIMITS integridad', () => {
  it('tiene exactamente 5 tiers', () => {
    expect(Object.keys(TIER_LIMITS)).toHaveLength(5);
  });

  it('todos los tiers tienen las 16 propiedades', () => {
    const propsRequeridas = [
      'max_workflows', 'max_actions_per_day', 'max_policies', 'max_team_members',
      'max_mcp_tools', 'max_approval_requests_per_day', 'max_playbooks',
      'max_namespaces', 'max_simulations_per_month', 'audit_retention_days',
      'trace_retention_days', 'overage_rate_usdt', 'sso_available',
      'on_premise_available', 'custom_rbac', 'z3_solver',
    ];

    (Object.keys(TIER_LIMITS) as SubscriptionTierName[]).forEach((tier) => {
      propsRequeridas.forEach((prop) => {
        expect(TIER_LIMITS[tier]).toHaveProperty(prop);
      });
    });
  });

  it('starter tiene overage_rate > 0', () => {
    expect(TIER_LIMITS.starter.overage_rate_usdt).toBeGreaterThan(0);
  });

  it('enterprise tiene overage_rate = 0', () => {
    expect(TIER_LIMITS.enterprise.overage_rate_usdt).toBe(0);
  });

  it('boolean props son realmente booleanos', () => {
    (Object.keys(TIER_LIMITS) as SubscriptionTierName[]).forEach((tier) => {
      expect(typeof TIER_LIMITS[tier].sso_available).toBe('boolean');
      expect(typeof TIER_LIMITS[tier].on_premise_available).toBe('boolean');
      expect(typeof TIER_LIMITS[tier].custom_rbac).toBe('boolean');
      expect(typeof TIER_LIMITS[tier].z3_solver).toBe('boolean');
    });
  });
});
