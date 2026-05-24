"use client";

import { useCallback } from "react";
import {
  Shield,
  Lock,
  KeyRound,
  Box,
  ShieldCheck,
  FileLock,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FEATURE_TIER_MAP } from "@/lib/pricing-engine/types";
import type { FeatureName } from "@/lib/pricing-engine/types";
import { iconoCapa } from "@/app/_page_parts/utils";
import { useDashboardData } from "@/hooks/useDashboardData";
import { WidgetBloqueado } from "@/app/_page_parts/components/WidgetBloqueado";
import { useSubscriptionContext } from "@/hooks/useUserProfile";

export default function BovedaPage() {
  const { capas, reglasDenegacion, ledger, cargando } = useDashboardData();

  // Sprint 6: Real subscription tier from user profile
  const { ctx: ctxSuscripcion } = useSubscriptionContext();
  const featureDisponible = useCallback(
    (feature: FeatureName): boolean => {
      const tiers = FEATURE_TIER_MAP[feature];
      return tiers?.includes(ctxSuscripcion.tier) ?? false;
    },
    [ctxSuscripcion.tier]
  );

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-pulse text-muted-foreground">
          Cargando Bóveda...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Capas de Defensa */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-500" />
            Capas de Defensa
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {capas.map((capa) => (
              <div
                key={capa.id}
                className="p-4 rounded-xl border border-border bg-card hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                    {iconoCapa(capa.icon)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">
                      {capa.name}
                    </p>
                    <Badge
                      className={`text-[8px] px-1.5 py-0 border-0 font-bold ${
                        capa.status === "active"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
                      }`}
                    >
                      {capa.status === "active" ? "ACTIVA" : "INACTIVA"}
                    </Badge>
                  </div>
                </div>
                <p className="text-[11px] text-muted-foreground line-clamp-2">
                  {capa.description}
                </p>
                {capa.details && (
                  <p className="text-[10px] text-muted-foreground/60 mt-1 line-clamp-1">
                    {capa.details}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Reglas de Denegación */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
            <Lock className="h-4 w-4 text-red-500" />
            Reglas de Denegación Absoluta
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="max-h-96">
            <div className="space-y-2">
              {reglasDenegacion.map((regla) => (
                <div
                  key={regla.id}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border bg-card"
                >
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${regla.locked ? "bg-red-500" : "bg-amber-400"}`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-foreground truncate">
                      {regla.rule}
                    </p>
                    <p className="text-[10px] text-muted-foreground line-clamp-1">
                      {regla.description}
                    </p>
                  </div>
                  <Badge className="text-[8px] px-1.5 py-0 border-0 bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-white/60 font-bold shrink-0">
                    {regla.niche}
                  </Badge>
                  {regla.locked && (
                    <Lock className="h-3 w-3 text-red-400 shrink-0" />
                  )}
                </div>
              ))}
              {reglasDenegacion.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  No hay reglas de denegación configuradas
                </p>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Feature gate */}
      {!featureDisponible("AuditMerkleChain" as FeatureName) && (
        <WidgetBloqueado
          etiqueta="Cadena Merkle Completa"
          descripcion="Registro inmutable con verificación criptográfica BLAKE3"
          tierRequerido="business"
        />
      )}
    </div>
  );
}
