"use client";

import useSWR from 'swr';
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
} from '@/app/_page_parts/types';
import type { ApiError } from '@/lib/api-client';

// Re-export the old interface for backward compatibility
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

/** Helper: extract ApiError from SWR error */
function toApiError(err: unknown): ApiError | null {
  if (!err) return null;
  if (typeof err === 'object' && err !== null && 'status' in err) return err as ApiError;
  if (err instanceof Error) return { message: err.message || 'Error desconocido', code: 'UNKNOWN', status: 500 };
  return { message: 'Error desconocido', code: 'UNKNOWN', status: 500 };
}

/**
 * Sprint 7: SWR-powered dashboard data hook.
 * Each endpoint is fetched independently with SWR — no more manual polling.
 * The SSE real-time hook (useRealtimeEvents) can trigger revalidation.
 */
export function useDashboardData(_pollInterval?: number): DashboardData {
  // SWR for each endpoint — refreshInterval as fallback; SSE triggers revalidation
  const { data: metricas, error: errMetricas, mutate: mutMetricas } = useSWR<MetricasDashboard>(
    '/api/dashboard/metrics',
    { refreshInterval: 30000 }
  );
  const { data: propuestasRaw, error: errPropuestas, mutate: mutPropuestas } = useSWR<{ proposals: PropuestaMemoria[] }>(
    '/api/dashboard/memory-proposals',
    { refreshInterval: 30000 }
  );
  const { data: alertasRaw, error: errAlertas, mutate: mutAlertas } = useSWR<{ alerts: AlertaSNA[] }>(
    '/api/dashboard/sna-alerts',
    { refreshInterval: 15000 }
  );
  const { data: ledgerRaw, error: errLedger, mutate: mutLedger } = useSWR<{ entries: EntradaLedger[] }>(
    '/api/dashboard/ledger',
    { refreshInterval: 30000 }
  );
  const { data: pipeline, error: errPipeline, mutate: mutPipeline } = useSWR<EstadoPipeline>(
    '/api/dashboard/pipeline-status',
    { refreshInterval: 10000 }
  );
  const { data: capasRaw, error: errCapas, mutate: mutCapas } = useSWR<{ layers: CapaDefensa[] }>(
    '/api/dashboard/defense-layers',
    { refreshInterval: 60000 }
  );
  const { data: reglasRaw, error: errReglas, mutate: mutReglas } = useSWR<{ rules: ReglaDenegacion[] }>(
    '/api/dashboard/deny-rules',
    { refreshInterval: 60000 }
  );
  const { data: roi, error: errROI, mutate: mutROI } = useSWR<DatosROI>(
    '/api/dashboard/roi',
    { refreshInterval: 30000 }
  );
  const { data: nichosRaw, error: errNichos, mutate: mutNichos } = useSWR<{ niches: Nicho[] }>(
    '/api/dashboard/niches',
    { refreshInterval: 60000 }
  );
  const { data: actividadesRaw, error: errActividades, mutate: mutActividades } = useSWR<{ activities: ItemActividad[] }>(
    '/api/dashboard/activity',
    { refreshInterval: 15000 }
  );

  // Extract data from wrapped responses
  const propuestas = propuestasRaw?.proposals || [];
  const alertasSNA = alertasRaw?.alerts || [];
  const ledger = ledgerRaw?.entries || [];
  const capas = capasRaw?.layers || [];
  const reglasDenegacion = reglasRaw?.rules || [];
  const nichos = nichosRaw?.niches || [];
  const actividades = actividadesRaw?.activities || [];

  // Aggregate loading state
  const anyLoading = [
    !metricas && !errMetricas,
    !propuestasRaw && !errPropuestas,
    !alertasRaw && !errAlertas,
    !ledgerRaw && !errLedger,
    !pipeline && !errPipeline,
  ].some(Boolean);

  // Aggregate errors
  const errores: DashboardErrors = {
    metricas: toApiError(errMetricas),
    propuestas: toApiError(errPropuestas),
    alertasSNA: toApiError(errAlertas),
    ledger: toApiError(errLedger),
    pipeline: toApiError(errPipeline),
    capas: toApiError(errCapas),
    reglasDenegacion: toApiError(errReglas),
    roi: toApiError(errROI),
    nichos: toApiError(errNichos),
    actividades: toApiError(errActividades),
  };

  const tieneErrores = Object.values(errores).some((e) => e !== null);

  // Reload all
  const recargar = () => {
    mutMetricas();
    mutPropuestas();
    mutAlertas();
    mutLedger();
    mutPipeline();
    mutCapas();
    mutReglas();
    mutROI();
    mutNichos();
    mutActividades();
  };

  return {
    metricas: metricas ?? null,
    propuestas,
    alertasSNA,
    ledger,
    pipeline: pipeline ?? null,
    capas,
    reglasDenegacion,
    roi: roi ?? null,
    nichos,
    actividades,
    cargando: anyLoading,
    errores,
    tieneErrores,
    ultimaActualizacion: new Date(),
    recargar,
  };
}
