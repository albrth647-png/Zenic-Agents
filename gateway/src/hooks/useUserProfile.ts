"use client";

import useSWR from 'swr';
import { useSession } from "next-auth/react";
import type { ApiError } from "@/lib/api-client";
import type { SubscriptionTierName } from "@/lib/pricing-engine/types";
import { construirContextoSuscripcion } from "@/app/_page_parts/constants";
import type { ContextoSuscripcion } from "@/app/_page_parts/types";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 7: useUserProfile + useSubscriptionContext
// - Now uses SWR for caching, deduplication, and automatic revalidation
// - Derives subscription tier from user role instead of hardcoding "enterprise"
// - Provides a proper ContextoSuscripcion based on real session data
// ═══════════════════════════════════════════════════════════════════════════════

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar: string | null;
  role: string;
  status: string;
  isActive: boolean;
  lastLogin: string | null;
  createdAt: string;
  updatedAt: string;
  subscriptionTier: string;
  rbacRoles: Array<{ name: string; description: string }>;
  activeSessions: number;
}

export function useUserProfile() {
  const { status: sessionStatus } = useSession();
  const isAuthenticated = sessionStatus === "authenticated";

  const { data: profile, error, mutate } = useSWR<UserProfile>(
    isAuthenticated ? '/api/user/profile' : null,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  return {
    profile: profile ?? null,
    cargando: !profile && !error && isAuthenticated,
    error: error as ApiError | null,
    recargar: mutate,
  };
}

/**
 * Derives subscription context from real user profile data.
 * Falls back to "starter" tier when profile isn't loaded yet.
 * Replaces the old hardcoded construirContextoSuscripcion("enterprise") pattern.
 */
export function useSubscriptionContext(): {
  ctx: ContextoSuscripcion;
  cargando: boolean;
} {
  const { profile, cargando } = useUserProfile();

  // Map role to tier with safe fallback
  const tier = ((): SubscriptionTierName => {
    if (!profile) return "starter"; // Safe default while loading
    const t = profile.subscriptionTier;
    // Validate it's a known tier
    if (["starter", "business", "enterprise", "on_premise_enterprise"].includes(t)) {
      return t as SubscriptionTierName;
    }
    return "starter";
  })();

  const ctx = construirContextoSuscripcion(tier);

  return { ctx, cargando };
}
