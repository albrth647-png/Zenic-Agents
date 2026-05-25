"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type {
  MetricasDashboard,
  PropuestaMemoria,
  AlertaSNA,
  EntradaLedger,
  EstadoPipeline,
  CapaDefensa,
  ReglaDenegacion,
  DatosROI,
  Nicho,
  ItemActividad,
} from "@/app/_page_parts/types";
import type { ApiError } from "@/lib/api-client";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Refactored useDashboardData
// - Exposes per-endpoint errors (no more swallowing)
// - Uses AbortController for cleanup
// - Tracks which endpoints failed for targeted error UI
// ═══════════════════════════════════════════════════════════════════════════════

export interface DashboardErrors {
  metricas: ApiError | null;
  propuestas: ApiError | null;
  alertasSNA: ApiError | null;
  ledger: ApiError | null;
  pipeline: ApiError | null;
  capas: ApiError | null;
  reglasDenegacion: ApiError | null;
  roi: ApiError | null;
  nichos: ApiError | null;
  actividades: ApiError | null;
}

export interface DashboardData {
  metricas: MetricasDashboard | null;
  propuestas: PropuestaMemoria[];
  alertasSNA: AlertaSNA[];
  ledger: EntradaLedger[];
  pipeline: EstadoPipeline | null;
  capas: CapaDefensa[];
  reglasDenegacion: ReglaDenegacion[];
  roi: DatosROI | null;
  nichos: Nicho[];
  actividades: ItemActividad[];
  cargando: boolean;
  errores: DashboardErrors;
  tieneErrores: boolean;
  ultimaActualizacion: Date | null;
  recargar: () => void;
}

const EMPTY_ERRORS: DashboardErrors = {
  metricas: null,
  propuestas: null,
  alertasSNA: null,
  ledger: null,
  pipeline: null,
  capas: null,
  reglasDenegacion: null,
  roi: null,
  nichos: null,
  actividades: null,
};

/** Parse a single API response, returning data or error */
async function parseResponse<T>(
  res: Response | null,
  extractData: (json: any) => T,
  fallback: T
): Promise<{ data: T; error: ApiError | null }> {
  if (!res) {
    return { data: fallback, error: { message: "Sin respuesta del servidor", code: "NO_RESPONSE", status: 0 } };
  }
  if (!res.ok) {
    let msg = `Error ${res.status}`;
    try {
      const body = await res.json();
      msg = body.error || body.message || msg;
    } catch { /* ignore parse error */ }
    return { data: fallback, error: { message: msg, code: "HTTP_ERROR", status: res.status } };
  }
  try {
    const json = await res.json();
    return { data: extractData(json), error: null };
  } catch {
    return { data: fallback, error: { message: "Error al procesar respuesta", code: "PARSE_ERROR", status: 500 } };
  }
}

export function useDashboardData(pollInterval = 15000): DashboardData {
  const [metricas, setMetricas] = useState<MetricasDashboard | null>(null);
  const [propuestas, setPropuestas] = useState<PropuestaMemoria[]>([]);
  const [alertasSNA, setAlertasSNA] = useState<AlertaSNA[]>([]);
  const [ledger, setLedger] = useState<EntradaLedger[]>([]);
  const [pipeline, setPipeline] = useState<EstadoPipeline | null>(null);
  const [capas, setCapas] = useState<CapaDefensa[]>([]);
  const [reglasDenegacion, setReglasDenegacion] = useState<ReglaDenegacion[]>([]);
  const [roi, setROI] = useState<DatosROI | null>(null);
  const [nichos, setNichos] = useState<Nicho[]>([]);
  const [actividades, setActividades] = useState<ItemActividad[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errores, setErrores] = useState<DashboardErrors>(EMPTY_ERRORS);
  const [ultimaActualizacion, setUltimaActualizacion] = useState<Date | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const cargarTodo = useCallback(async () => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const { signal } = controller;

    const urls = [
      "/api/dashboard/metrics",
      "/api/dashboard/memory-proposals",
      "/api/dashboard/sna-alerts",
      "/api/dashboard/ledger",
      "/api/dashboard/pipeline-status",
      "/api/dashboard/defense-layers",
      "/api/dashboard/deny-rules",
      "/api/dashboard/roi",
      "/api/dashboard/niches",
      "/api/dashboard/activity",
    ] as const;

    // Fire all requests in parallel
    const responses = await Promise.allSettled(
      urls.map((url) => fetch(url, { signal }).catch(() => null))
    );

    // If aborted, skip processing
    if (signal.aborted) return;

    // Process each response individually, capturing errors
    const newErrors: DashboardErrors = { ...EMPTY_ERRORS };

    // 0: metrics
    {
      const r = responses[0];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<MetricasDashboard | null>(
        raw as Response | null,
        (json) => json,
        null
      );
      setMetricas(data);
      newErrors.metricas = error;
    }

    // 1: proposals
    {
      const r = responses[1];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<PropuestaMemoria[]>(
        raw as Response | null,
        (json) => json.proposals || [],
        []
      );
      setPropuestas(data);
      newErrors.propuestas = error;
    }

    // 2: SNA alerts
    {
      const r = responses[2];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<AlertaSNA[]>(
        raw as Response | null,
        (json) => json.alerts || [],
        []
      );
      setAlertasSNA(data);
      newErrors.alertasSNA = error;
    }

    // 3: ledger
    {
      const r = responses[3];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<EntradaLedger[]>(
        raw as Response | null,
        (json) => json.entries || [],
        []
      );
      setLedger(data);
      newErrors.ledger = error;
    }

    // 4: pipeline
    {
      const r = responses[4];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<EstadoPipeline | null>(
        raw as Response | null,
        (json) => json,
        null
      );
      setPipeline(data);
      newErrors.pipeline = error;
    }

    // 5: defense layers
    {
      const r = responses[5];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<CapaDefensa[]>(
        raw as Response | null,
        (json) => json.layers || [],
        []
      );
      setCapas(data);
      newErrors.capas = error;
    }

    // 6: deny rules
    {
      const r = responses[6];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<ReglaDenegacion[]>(
        raw as Response | null,
        (json) => json.rules || [],
        []
      );
      setReglasDenegacion(data);
      newErrors.reglasDenegacion = error;
    }

    // 7: ROI
    {
      const r = responses[7];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<DatosROI | null>(
        raw as Response | null,
        (json) => json,
        null
      );
      setROI(data);
      newErrors.roi = error;
    }

    // 8: niches
    {
      const r = responses[8];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<Nicho[]>(
        raw as Response | null,
        (json) => json.niches || [],
        []
      );
      setNichos(data);
      newErrors.nichos = error;
    }

    // 9: activities
    {
      const r = responses[9];
      const raw = r.status === "fulfilled" ? r.value : null;
      const { data, error } = await parseResponse<ItemActividad[]>(
        raw as Response | null,
        (json) => json.activities || [],
        []
      );
      setActividades(data);
      newErrors.actividades = error;
    }

    setErrores(newErrors);
    setUltimaActualizacion(new Date());
    setCargando(false);
  }, []);

  useEffect(() => {
    cargarTodo();
    const intervalo = setInterval(cargarTodo, pollInterval);
    return () => {
      clearInterval(intervalo);
      abortRef.current?.abort();
    };
  }, [cargarTodo, pollInterval]);

  const tieneErrores = Object.values(errores).some((e) => e !== null);

  return {
    metricas,
    propuestas,
    alertasSNA,
    ledger,
    pipeline,
    capas,
    reglasDenegacion,
    roi,
    nichos,
    actividades,
    cargando,
    errores,
    tieneErrores,
    ultimaActualizacion,
    recargar: cargarTodo,
  };
}
