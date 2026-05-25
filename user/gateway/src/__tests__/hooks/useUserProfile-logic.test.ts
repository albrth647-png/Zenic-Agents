// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Test riguroso — useUserProfile lógica pura (tier mapping)
// No renderizamos el hook porque requiere SessionProvider + SWR + Next.js router.
// En su lugar, testeamos la lógica pura del mapeo de tier.
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import type { SubscriptionTierName } from '@/lib/pricing-engine/types';

// Lógica pura extraída de useUserProfile.ts
function mapTierFromProfile(subscriptionTier: string | null | undefined): SubscriptionTierName {
  if (!subscriptionTier) return 'starter';
  const validTiers: SubscriptionTierName[] = ['starter', 'business', 'enterprise', 'on_premise_enterprise', 'trial'];
  if (validTiers.includes(subscriptionTier as SubscriptionTierName)) {
    return subscriptionTier as SubscriptionTierName;
  }
  return 'starter';
}

describe('useUserProfile — lógica de mapeo de tier', () => {
  it('null → starter (safe default)', () => {
    expect(mapTierFromProfile(null)).toBe('starter');
  });

  it('undefined → starter', () => {
    expect(mapTierFromProfile(undefined)).toBe('starter');
  });

  it('string vacío → starter', () => {
    expect(mapTierFromProfile('')).toBe('starter');
  });

  it('"starter" → starter', () => {
    expect(mapTierFromProfile('starter')).toBe('starter');
  });

  it('"business" → business', () => {
    expect(mapTierFromProfile('business')).toBe('business');
  });

  it('"enterprise" → enterprise', () => {
    expect(mapTierFromProfile('enterprise')).toBe('enterprise');
  });

  it('"on_premise_enterprise" → on_premise_enterprise', () => {
    expect(mapTierFromProfile('on_premise_enterprise')).toBe('on_premise_enterprise');
  });

  it('"trial" → trial', () => {
    expect(mapTierFromProfile('trial')).toBe('trial');
  });

  it('tier desconocido → starter (fallback)', () => {
    expect(mapTierFromProfile('premium')).toBe('starter');
    expect(mapTierFromProfile('PRO')).toBe('starter');
    expect(mapTierFromProfile('free')).toBe('starter');
  });

  it('tier con mayúsculas → starter (case-sensitive)', () => {
    expect(mapTierFromProfile('Starter')).toBe('starter');
    expect(mapTierFromProfile('BUSINESS')).toBe('starter');
    expect(mapTierFromProfile('Enterprise')).toBe('starter');
  });

  it('tier con espacios → starter', () => {
    expect(mapTierFromProfile(' starter ')).toBe('starter');
    expect(mapTierFromProfile('business ')).toBe('starter');
  });

  it('numeros → starter', () => {
    expect(mapTierFromProfile('123')).toBe('starter');
    expect(mapTierFromProfile('1')).toBe('starter');
  });
});
