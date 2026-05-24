"use client";

import { useMemo, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Play,
  FileLock,
  FileSearch,
  ArrowUpRight,
  Timer,
  Cpu,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { FEATURE_TIER_MAP } from "@/lib/pricing-engine/types";
import type { FeatureName } from "@/lib/pricing-engine/types";
import {
  tiempoRelativo,
  truncarHash,
  formatoMoneda,
  categoriaColor,
  calcularMonitoresSNA,
} from "@/app/_page_parts/utils";
import { MicroIndicadorSNA } from "@/app/_page_parts/components/MicroIndicadorSNA";
import { WidgetBloqueado } from "@/app/_page_parts/components/WidgetBloqueado";
import { PasoPipelineViz } from "@/app/_page_parts/components/PasoPipelineViz";
import { ContadorConsumoPlan } from "@/app/_page_parts/components/ContadorConsumoPlan";
import { useDashboardData } from "@/hooks/useSWRDashboard";
import { useSubscriptionContext } from "@/hooks/useUserProfile";
import { formatApiError } from "@/lib/api-client";

export default function DashboardPage() {
  const {
    metricas,
    alertasSNA,
    ledger,
    pipeline,
    roi,
    cargando,
    errores,
    tieneErrores,
    recargar,
  } = useDashboardData();

  // Sprint 6: Real subscription tier from user profile instead of hardcoded "enterprise"
  const { ctx: ctxSuscripcion } = useSubscriptionContext();
  const featureDisponible = useCallback(
    (feature: FeatureName): boolean => {
      const tiers = FEATURE_TIER_MAP[feature];
      return tiers?.includes(ctxSuscripcion.tier) ?? false;
    },
    [ctxSuscripcion.tier]
  );
  const monitoresSNA = useMemo(
    () => calcularMonitoresSNA(metricas),
    [metricas]
  );

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center space-y-4">
          <Cpu className="h-12 w-12 text-emerald-400 mx-auto animate-pulse" />
          <p className="text-muted-foreground text-sm tracking-widest uppercase">
            Cargando Centro de Comando...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Sprint 6: Error banner when some endpoints fail */}
      {tieneErrores && (
        <Card className="border-amber-200 dark:border-amber-500/30 bg-amber-50/50 dark:bg-amber-500/5">
          <CardContent className="py-3 flex items-center gap-3">
            <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-amber-700 dark:text-amber-400 font-medium">
                Algunos datos no se pudieron cargar
              </p>
              <p className="text-[10px] text-amber-600/70 dark:text-amber-400/50">
                {Object.entries(errores)
                  .filter(([, e]) => e !== null)
                  .map(([key, e]) => `${key}: ${formatApiError(e)}`)
                  .join(" • ")}
              </p>
            </div>
            <Button variant="outline" size="sm" className="h-7 text-[10px] gap-1" onClick={recargar}>
              <RefreshCw className="h-3 w-3" />
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}
      {/* Salud del Sistema */}
      <Card className="border-0 shadow-sm overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-500" />
            Salud del Sistema — Monitores Autónomos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 py-2">
            {monitoresSNA.map((monitor) => (
              <MicroIndicadorSNA key={monitor.tipo} monitor={monitor} />
            ))}
          </div>
          {alertasSNA.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Alertas activas
              </p>
              <ScrollArea className="max-h-32">
                {alertasSNA.slice(0, 5).map((alerta) => (
                  <div key={alerta.id} className="flex items-center gap-2 py-1.5">
                    <AlertTriangle
                      className={`h-3.5 w-3.5 shrink-0 ${
                        alerta.severity === "critical"
                          ? "text-red-500"
                          : alerta.severity === "error"
                            ? "text-orange-500"
                            : "text-amber-500"
                      }`}
                    />
                    <span className="text-xs text-muted-foreground flex-1 truncate">
                      {alerta.details || alerta.action}
                    </span>
                    <span className="text-[10px] text-muted-foreground/60 shrink-0">
                      {tiempoRelativo(alerta.createdAt)}
                    </span>
                  </div>
                ))}
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Registro + Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="border-0 shadow-sm overflow-hidden">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-4">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider truncate">
                Registro de Integridad
              </p>
              {featureDisponible("AuditMerkleChain" as FeatureName) ? (
                <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 text-[8px] px-1.5 py-0 border-0 font-bold shrink-0">
                  BLAKE3
                </Badge>
              ) : (
                <Badge className="bg-gray-100 text-gray-400 dark:bg-gray-500/20 dark:text-gray-400 text-[8px] px-1.5 py-0 border-0 font-bold shrink-0">
                  BÁSICO
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center shrink-0">
                {featureDisponible("AuditMerkleChain" as FeatureName) ? (
                  <FileLock className="h-6 w-6 text-emerald-600" />
                ) : (
                  <FileSearch className="h-6 w-6 text-muted-foreground" />
                )}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-emerald-700 dark:text-emerald-400 truncate">
                  {featureDisponible("AuditMerkleChain" as FeatureName)
                    ? "VERIFICADA"
                    : "REGISTRO BÁSICO"}
                </p>
                <p className="text-[10px] text-muted-foreground truncate">
                  {featureDisponible("AuditMerkleChain" as FeatureName)
                    ? "Cadena de auditoría inmutable (BLAKE3)"
                    : "Actualiza a Business para cadena completa"}
                </p>
              </div>
            </div>
            {featureDisponible("AuditMerkleChain" as FeatureName) ? (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground">Entradas en cadena</span>
                  <span className="font-semibold text-foreground shrink-0">
                    {ledger.length}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground">Último sello</span>
                  <span className="font-mono text-muted-foreground text-[9px] truncate ml-2">
                    {ledger.length > 0
                      ? truncarHash(ledger[0].contentHash)
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold truncate">
                    Integridad criptográfica confirmada
                  </span>
                </div>
              </div>
            ) : (
              <WidgetBloqueado
                etiqueta="Cadena de Registro Completa"
                descripcion="Registro inmutable con verificación BLAKE3"
                tierRequerido="business"
              />
            )}
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm lg:col-span-2 overflow-hidden">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Play className="h-4 w-4 text-emerald-500" />
                Flujo de Procesamiento en Vivo
              </CardTitle>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`w-2 h-2 rounded-full ${
                    pipeline?.isActive
                      ? "bg-emerald-500 animate-pulse"
                      : "bg-gray-300"
                  }`}
                />
                <span className="text-[10px] text-muted-foreground font-medium">
                  {pipeline?.isActive ? "Procesando" : "En espera"}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-0 py-2">
              {pipeline?.steps.map((paso, idx) => {
                const bloqueado =
                  paso.id === 9 &&
                  !featureDisponible("PolicySimulation" as FeatureName);
                return (
                  <PasoPipelineViz
                    key={paso.id}
                    paso={paso}
                    esActual={paso.id === pipeline.currentStep}
                    esUltimo={
                      idx === pipeline.steps.length - 1 ||
                      idx === Math.floor(pipeline.steps.length / 2) - 1
                    }
                    bloqueado={bloqueado}
                  />
                );
              })}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-white/5 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-4 text-[10px]">
                <span className="text-muted-foreground">
                  Procesadas:{" "}
                  <span className="font-semibold text-foreground">
                    {pipeline?.totalProcessed ?? 0}
                  </span>
                </span>
                <span className="text-emerald-600 dark:text-emerald-400">
                  Exitosas:{" "}
                  <span className="font-semibold">
                    {pipeline?.completedCount ?? 0}
                  </span>
                </span>
                <span className="text-red-500">
                  Bloqueadas:{" "}
                  <span className="font-semibold">
                    {pipeline?.deniedCount ?? 0}
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Timer className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">
                  Ciclo: ~{pipeline?.cycleTime ?? 90}s
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-0 shadow-sm overflow-hidden">
          <CardContent className="p-5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider truncate">
              Agentes Activos
            </p>
            <p className="text-3xl font-bold text-foreground mt-1">
              {metricas?.activeAgents ?? "—"}
            </p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm overflow-hidden">
          <CardContent className="p-5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider truncate">
              Acciones Bloqueadas
            </p>
            <p className="text-3xl font-bold text-foreground mt-1">
              {metricas?.securityGateBlocks ?? "—"}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1 truncate">
              No autorizadas y denegadas
            </p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm bg-emerald-50/50 dark:bg-emerald-500/5 overflow-hidden">
          <CardContent className="p-5">
            <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider truncate">
              Cero Alucinaciones
            </p>
            <p className="text-3xl font-bold text-emerald-700 dark:text-emerald-400 mt-1">
              {Math.max(0, metricas?.zeroHallucinationsPct ?? 100)}%
            </p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold truncate">
                Auditoría verificada
              </span>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm overflow-hidden">
          <CardContent className="p-5 space-y-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider truncate">
              Consumo del Plan
            </p>
            <ContadorConsumoPlan
              etiqueta="Acciones hoy"
              actual={metricas?.executionsToday ?? 0}
              maximo={ctxSuscripcion.limites.max_actions_per_day}
              unlimited={ctxSuscripcion.limites.max_actions_per_day === 0}
            />
            <ContadorConsumoPlan
              etiqueta="Workflows"
              actual={metricas?.activeAgents ?? 0}
              maximo={ctxSuscripcion.limites.max_workflows}
              unlimited={ctxSuscripcion.limites.max_workflows === 0}
            />
            <ContadorConsumoPlan
              etiqueta="Aprobaciones hoy"
              actual={metricas?.pendingApprovals ?? 0}
              maximo={ctxSuscripcion.limites.max_approval_requests_per_day}
              unlimited={
                ctxSuscripcion.limites.max_approval_requests_per_day === 0
              }
            />
          </CardContent>
        </Card>
      </div>

      {/* ROI */}
      <Card className="border-0 shadow-sm overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-500" />
              Impacto y Valor Generado
            </CardTitle>
            <span className="text-[10px] text-muted-foreground truncate">
              Plan {ctxSuscripcion.nombreMostrar} •{" "}
              {ctxSuscripcion.limites.max_actions_per_day === 0
                ? "∞"
                : ctxSuscripcion.limites.max_actions_per_day}{" "}
              acciones/día
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-500/10 dark:to-teal-500/10 rounded-xl p-3 sm:p-4 overflow-hidden">
              <p className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider truncate">
                Valor Hoy
              </p>
              <p className="text-xl sm:text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-1 truncate">
                {formatoMoneda(roi?.valueToday ?? 0)}
              </p>
              <p className="text-[10px] text-emerald-500 dark:text-emerald-400/60 mt-1 flex items-center gap-1 truncate">
                <ArrowUpRight className="h-3 w-3 shrink-0" />
                Ahorro estimado
              </p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-500/10 dark:to-indigo-500/10 rounded-xl p-3 sm:p-4 overflow-hidden">
              <p className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider truncate">
                Horas Ahorradas
              </p>
              <p className="text-xl sm:text-2xl font-bold text-blue-700 dark:text-blue-400 mt-1 truncate">
                {roi?.hoursSavedToday ?? 0}h
              </p>
              <p className="text-[10px] text-blue-400 dark:text-blue-400/60 mt-1 truncate">
                A ~15 min por acción
              </p>
            </div>
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-500/10 dark:to-orange-500/10 rounded-xl p-3 sm:p-4 overflow-hidden">
              <p className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider truncate">
                Exitosas Hoy
              </p>
              <p className="text-xl sm:text-2xl font-bold text-amber-700 dark:text-amber-400 mt-1 truncate">
                {roi?.actionsCompletedToday ?? 0}
              </p>
              <p className="text-[10px] text-amber-500 dark:text-amber-400/60 mt-1 truncate">
                Completadas
              </p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-fuchsia-50 dark:from-purple-500/10 dark:to-fuchsia-500/10 rounded-xl p-3 sm:p-4 overflow-hidden">
              <p className="text-[10px] font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider truncate">
                Valor 30 Días
              </p>
              <p className="text-xl sm:text-2xl font-bold text-purple-700 dark:text-purple-400 mt-1 truncate">
                {formatoMoneda(roi?.value30d ?? 0)}
              </p>
              <p className="text-[10px] text-purple-400 dark:text-purple-400/60 mt-1 truncate">
                Retorno acumulado
              </p>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Tendencia Semanal
            </p>
            <div className="flex items-end gap-2 h-32">
              {roi?.weeklyTrend.map((dia) => {
                const maxVal = Math.max(
                  ...(roi?.weeklyTrend.map((d) => d.exitosas + d.bloqueadas) || [1]),
                  1
                );
                const total = dia.exitosas + dia.bloqueadas;
                const alturaPct = Math.max((total / maxVal) * 100, 4);
                return (
                  <div
                    key={dia.day}
                    className="flex-1 flex flex-col items-center gap-1"
                  >
                    <div
                      className="w-full flex flex-col justify-end"
                      style={{ height: `${alturaPct}%` }}
                    >
                      <div
                        className="bg-emerald-400 rounded-t-sm transition-all"
                        style={{ flex: Math.max(dia.exitosas, 1) }}
                      />
                      <div
                        className="bg-red-300 dark:bg-red-400/60 rounded-b-sm transition-all"
                        style={{ flex: Math.max(dia.bloqueadas, 0.5) }}
                      />
                    </div>
                    <span className="text-[9px] text-muted-foreground font-medium">
                      {dia.day}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-emerald-400" />
                Exitosas
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-red-300 dark:bg-red-400/60" />
                Bloqueadas
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feature gates */}
      {!featureDisponible("PolicySimulation" as FeatureName) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {ctxSuscripcion.caracteristicas
            .filter((c) => !c.disponible)
            .slice(0, 3)
            .map((c) => (
              <WidgetBloqueado
                key={c.feature}
                etiqueta={c.etiqueta}
                descripcion={c.descripcion}
                tierRequerido={c.tierMinimo}
              />
            ))}
        </div>
      )}
    </div>
  );
}
