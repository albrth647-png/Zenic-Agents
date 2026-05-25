"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import {
  Gavel,
  RefreshCw,
  CheckCircle2,
  Eye,
  XCircle,
  Scale,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { FEATURE_TIER_MAP } from "@/lib/pricing-engine/types";
import type { FeatureName } from "@/lib/pricing-engine/types";
import { tiempoRelativo, categoriaColor } from "@/app/_page_parts/utils";
import type { EvidenciaHITL } from "@/app/_page_parts/types";
import { useDashboardData } from "@/hooks/useDashboardData";
import { useSubscriptionContext } from "@/hooks/useUserProfile";

export default function ArbitrajePage() {
  const { propuestas, metricas, cargando } = useDashboardData();
  const [propuestaSeleccionada, setPropuestaSeleccionada] = useState<
    string | null
  >(null);
  const [evidencia, setEvidencia] = useState<EvidenciaHITL | null>(null);
  const [cargandoEvidencia, setCargandoEvidencia] = useState(false);
  const [checkEvidencia, setCheckEvidencia] = useState(false);
  const [justificacion, setJustificacion] = useState("");
  const [checkRiesgo, setCheckRiesgo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [sosteniendoBoton, setSosteniendoBoton] = useState(false);
  const sostenidoRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [localPropuestas, setLocalPropuestas] = useState(propuestas);

  // Sprint 6: Real subscription tier from user profile
  const { ctx: ctxSuscripcion } = useSubscriptionContext();
  const featureDisponible = useCallback(
    (feature: FeatureName): boolean => {
      const tiers = FEATURE_TIER_MAP[feature];
      return tiers?.includes(ctxSuscripcion.tier) ?? false;
    },
    [ctxSuscripcion.tier]
  );

  // Sync proposals from hook
  useMemo(() => {
    setLocalPropuestas(propuestas);
  }, [propuestas]);

  const cargarEvidencia = useCallback(async (requestId: string) => {
    setCargandoEvidencia(true);
    setPropuestaSeleccionada(requestId);
    setCheckEvidencia(false);
    setJustificacion("");
    setCheckRiesgo(false);
    try {
      const res = await fetch(
        `/api/dashboard/hitl-evidence?requestId=${requestId}`
      );
      if (res.ok) {
        setEvidencia(await res.json());
      }
    } catch (err) {
      console.error("Error cargando evidencia:", err);
    } finally {
      setCargandoEvidencia(false);
    }
  }, []);

  const manejarAccionHITL = useCallback(
    async (requestId: string, accion: "approve" | "reject") => {
      setEnviando(true);
      try {
        const res = await fetch(`/api/v1/hitl/${requestId}/${accion}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            justification: justificacion,
            admin_evidence_review: checkEvidencia,
            risk_acknowledgment: checkRiesgo,
          }),
        });
        if (res.ok) {
          setLocalPropuestas((prev) =>
            prev.filter((p) => p.requestId !== requestId)
          );
          setPropuestaSeleccionada(null);
          setEvidencia(null);
          setCheckEvidencia(false);
          setJustificacion("");
          setCheckRiesgo(false);
        }
      } catch (err) {
        console.error("Error en acción HITL:", err);
      } finally {
        setEnviando(false);
        setSosteniendoBoton(false);
      }
    },
    [justificacion, checkEvidencia, checkRiesgo]
  );

  const botonHabilitado =
    checkEvidencia && justificacion.length >= 50 && checkRiesgo;
  const iniciarSosten = () => {
    if (!botonHabilitado) return;
    setSosteniendoBoton(true);
    sostenidoRef.current = setTimeout(() => {
      if (evidencia) {
        manejarAccionHITL(evidencia.requestId, "approve");
      }
    }, 1500);
  };
  const cancelarSosten = () => {
    setSosteniendoBoton(false);
    if (sostenidoRef.current) {
      clearTimeout(sostenidoRef.current);
      sostenidoRef.current = null;
    }
  };

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 min-h-[500px]">
        {/* Bandeja de Veredictos */}
        <div className="lg:col-span-3">
          <Card className="border-0 shadow-sm h-full overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Gavel className="h-4 w-4 text-amber-500" />
                Bandeja de Veredictos
              </CardTitle>
              <p className="text-[10px] text-muted-foreground">
                {localPropuestas.length} solicitud
                {localPropuestas.length !== 1 ? "es" : ""} pendiente
                {localPropuestas.length !== 1 ? "s" : ""}
              </p>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-[460px]">
                {localPropuestas.length === 0 ? (
                  <div className="py-8 text-center">
                    <CheckCircle2 className="h-8 w-8 text-emerald-300 mx-auto mb-2" />
                    <p className="text-xs text-muted-foreground">
                      Sin solicitudes pendientes
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {localPropuestas.map((prop) => {
                      const cat =
                        prop.priority === "critical"
                          ? "destructive"
                          : prop.targetAction?.includes("financial")
                            ? "financial"
                            : "safe";
                      const colores = categoriaColor(cat);
                      const seleccionada =
                        propuestaSeleccionada === prop.requestId;
                      return (
                        <button
                          key={prop.id}
                          onClick={() => cargarEvidencia(prop.requestId)}
                          className={`w-full text-left rounded-xl border-2 p-3 transition-all overflow-hidden ${
                            seleccionada
                              ? `${colores.bg} ${colores.border} shadow-md`
                              : "border-border hover:border-gray-200 hover:shadow-sm"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5 gap-2">
                            <span
                              className={`text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 ${colores.bg} ${colores.text}`}
                            >
                              {colores.label}
                            </span>
                            <span className="text-[9px] text-muted-foreground shrink-0">
                              {tiempoRelativo(prop.createdAt)}
                            </span>
                          </div>
                          <p className="text-xs font-semibold text-foreground line-clamp-2">
                            {prop.title}
                          </p>
                          <p className="text-[10px] text-muted-foreground mt-1 line-clamp-1 truncate">
                            {prop.requesterName}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Visor de Evidencia */}
        <div className="lg:col-span-5">
          <Card className="border-0 shadow-sm h-full overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Eye className="h-4 w-4 text-blue-500" />
                Visor de Evidencia y Consenso
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!propuestaSeleccionada ? (
                <div className="py-16 text-center">
                  <Scale className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">
                    Seleccione una solicitud de la bandeja
                  </p>
                </div>
              ) : cargandoEvidencia ? (
                <div className="py-16 text-center">
                  <RefreshCw className="h-8 w-8 text-muted-foreground/30 mx-auto mb-3 animate-spin" />
                  <p className="text-xs text-muted-foreground">
                    Cargando evidencia...
                  </p>
                </div>
              ) : evidencia ? (
                <ScrollArea className="max-h-[520px]">
                  <div className="space-y-5 pr-2">
                    <div className="flex items-center justify-center">
                      <div
                        className={`px-8 py-4 rounded-2xl border-2 text-center ${
                          evidencia.llmVerdict
                            ? "bg-emerald-50 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/20"
                            : "bg-red-50 border-red-200 dark:bg-red-500/10 dark:border-red-500/20"
                        }`}
                      >
                        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                          Veredicto del Motor de IA
                        </p>
                        <p
                          className={`text-4xl font-black ${evidencia.llmVerdict ? "text-emerald-600" : "text-red-600"}`}
                        >
                          {evidencia.llmVerdict ? "SÍ" : "NO"}
                        </p>
                        <p className="text-[10px] text-muted-foreground mt-1">
                          {evidencia.llmVerdict
                            ? "La IA clasifica la acción como segura"
                            : "La IA clasifica la acción como riesgosa"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-center">
                      <span
                        className={`text-[10px] font-bold px-3 py-1 rounded-full ${categoriaColor(evidencia.category).bg} ${categoriaColor(evidencia.category).text}`}
                      >
                        Categoría: {categoriaColor(evidencia.category).label}
                      </span>
                    </div>
                    <Separator />
                    {featureDisponible("HitlEvidence" as FeatureName) ? (
                      <div>
                        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                          Balanzas de Evidencia
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <div className="flex items-center gap-1.5 mb-2">
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                              <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase">
                                A Favor
                              </span>
                            </div>
                            {evidencia.evidenceFor.map((ev, idx) => (
                              <div
                                key={idx}
                                className="bg-emerald-50 dark:bg-emerald-500/10 rounded-lg p-2.5 border border-emerald-100 dark:border-emerald-500/20 overflow-hidden"
                              >
                                <p className="text-[11px] text-emerald-800 dark:text-emerald-300 font-medium line-clamp-2">
                                  {ev.point}
                                </p>
                                <div className="flex items-center justify-between mt-1 gap-1">
                                  <span className="text-[9px] text-emerald-500 truncate">
                                    {ev.source}
                                  </span>
                                  <div className="flex items-center gap-1 shrink-0">
                                    <Progress
                                      value={ev.weight * 100}
                                      className="h-1 w-12"
                                    />
                                    <span className="text-[9px] text-emerald-400">
                                      {Math.round(ev.weight * 100)}%
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                            {evidencia.evidenceFor.length === 0 && (
                              <p className="text-[10px] text-muted-foreground/40 italic">
                                Sin evidencia a favor
                              </p>
                            )}
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center gap-1.5 mb-2">
                              <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
                              <span className="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase">
                                En Contra
                              </span>
                            </div>
                            {evidencia.evidenceAgainst.map((ev, idx) => (
                              <div
                                key={idx}
                                className="bg-red-50 dark:bg-red-500/10 rounded-lg p-2.5 border border-red-100 dark:border-red-500/20 overflow-hidden"
                              >
                                <p className="text-[11px] text-red-800 dark:text-red-300 font-medium line-clamp-2">
                                  {ev.point}
                                </p>
                                <div className="flex items-center justify-between mt-1 gap-1">
                                  <span className="text-[9px] text-red-500 truncate">
                                    {ev.source}
                                  </span>
                                  <div className="flex items-center gap-1 shrink-0">
                                    <Progress
                                      value={ev.weight * 100}
                                      className="h-1 w-12"
                                    />
                                    <span className="text-[9px] text-red-400">
                                      {Math.round(ev.weight * 100)}%
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                            {evidencia.evidenceAgainst.length === 0 && (
                              <p className="text-[10px] text-muted-foreground/40 italic">
                                Sin evidencia en contra
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-xs text-muted-foreground">
                          Las balanzas de evidencia requieren plan Business
                        </p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              ) : null}
            </CardContent>
          </Card>
        </div>

        {/* Panel de Acción */}
        <div className="lg:col-span-4">
          <Card className="border-0 shadow-sm h-full overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Gavel className="h-4 w-4 text-amber-500" />
                Panel de Decisión
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!evidencia ? (
                <div className="py-16 text-center">
                  <p className="text-sm text-muted-foreground">
                    Seleccione una solicitud para emitir un veredicto
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={checkEvidencia}
                        onCheckedChange={setCheckEvidencia}
                      />
                      <span className="text-xs text-foreground">
                        He revisado la evidencia
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={checkRiesgo}
                        onCheckedChange={setCheckRiesgo}
                      />
                      <span className="text-xs text-foreground">
                        Acepto la responsabilidad de la decisión
                      </span>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">
                      Justificación (mín. 50 caracteres)
                    </label>
                    <Textarea
                      value={justificacion}
                      onChange={(e) => setJustificacion(e.target.value)}
                      placeholder="Explica tu decisión..."
                      className="text-xs min-h-[80px]"
                    />
                    <p className="text-[9px] text-muted-foreground mt-1">
                      {justificacion.length}/50 caracteres mínimos
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                      disabled={!botonHabilitado || enviando}
                      onMouseDown={iniciarSosten}
                      onMouseUp={cancelarSosten}
                      onMouseLeave={cancelarSosten}
                    >
                      {sosteniendoBoton
                        ? "Mantén pulsado..."
                        : "Mantén para APROBAR"}
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      disabled={!botonHabilitado || enviando}
                      onClick={() =>
                        evidencia &&
                        manejarAccionHITL(evidencia.requestId, "reject")
                      }
                    >
                      RECHAZAR
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
