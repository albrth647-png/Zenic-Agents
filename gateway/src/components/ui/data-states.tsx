"use client";

import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import type { ApiError } from "@/lib/api-client";
import { formatApiError } from "@/lib/api-client";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Reusable Empty State + Error State + Loading State components
// These replace scattered inline empty/error/loading patterns across pages.
// ═══════════════════════════════════════════════════════════════════════════════

interface EstadoVacioProps {
  /** Icon to display (defaults to Inbox) */
  icon?: LucideIcon;
  /** Primary message */
  titulo: string;
  /** Secondary description */
  descripcion?: string;
  /** Optional action button */
  accion?: {
    etiqueta: string;
    onClick: () => void;
  };
  /** Size variant */
  compacto?: boolean;
}

/**
 * Empty state — shown when a data collection has zero items.
 * Replaces all "Sin datos" / "No hay X" inline patterns.
 */
export function EstadoVacio({
  icon: Icon,
  titulo,
  descripcion,
  accion,
  compacto = false,
}: EstadoVacioProps) {
  const size = compacto ? "h-8 w-8" : "h-12 w-12";
  const padding = compacto ? "py-6" : "py-12";

  return (
    <div className={`${padding} text-center`}>
      {Icon && (
        <Icon
          className={`${size} text-muted-foreground/20 mx-auto ${compacto ? "mb-2" : "mb-3"}`}
        />
      )}
      <p
        className={`text-muted-foreground font-medium ${compacto ? "text-xs" : "text-sm"}`}
      >
        {titulo}
      </p>
      {descripcion && (
        <p className="text-xs text-muted-foreground/60 mt-1 max-w-sm mx-auto">
          {descripcion}
        </p>
      )}
      {accion && (
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={accion.onClick}
        >
          {accion.etiqueta}
        </Button>
      )}
    </div>
  );
}

interface EstadoErrorProps {
  /** The API error to display */
  error: ApiError | null;
  /** Optional title override (default: "Error al cargar datos") */
  titulo?: string;
  /** Retry handler */
  onReintentar?: () => void;
  /** Compact variant */
  compacto?: boolean;
}

/**
 * Error state — shown when an API call fails.
 * Provides user-friendly message and retry button.
 */
export function EstadoError({
  error,
  titulo = "Error al cargar datos",
  onReintentar,
  compacto = false,
}: EstadoErrorProps) {
  if (!error) return null;

  const padding = compacto ? "py-4" : "py-8";
  const iconSize = compacto ? "h-6 w-6" : "h-10 w-10";

  return (
    <div className={`${padding} text-center`}>
      <div
        className={`${iconSize} rounded-full bg-red-500/10 flex items-center justify-center mx-auto ${compacto ? "mb-2" : "mb-3"}`}
      >
        <svg
          className={`${compacto ? "h-3.5 w-3.5" : "h-5 w-5"} text-red-400`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <p
        className={`text-foreground font-medium ${compacto ? "text-xs" : "text-sm"}`}
      >
        {titulo}
      </p>
      <p className="text-xs text-muted-foreground/70 mt-1 max-w-sm mx-auto">
        {formatApiError(error)}
      </p>
      {onReintentar && (
        <Button
          variant="outline"
          size="sm"
          className="mt-3 gap-1.5"
          onClick={onReintentar}
        >
          <RefreshCw className="h-3 w-3" />
          Reintentar
        </Button>
      )}
    </div>
  );
}

interface EstadoCargandoProps {
  /** Loading message */
  mensaje?: string;
  /** Compact variant */
  compacto?: boolean;
}

/**
 * Loading state — shown while data is being fetched.
 * Replaces scattered "Cargando..." patterns.
 */
export function EstadoCargando({
  mensaje = "Cargando...",
  compacto = false,
}: EstadoCargandoProps) {
  const padding = compacto ? "py-4" : "py-12";

  return (
    <div className={`${padding} text-center`}>
      <div
        className={`${compacto ? "h-6 w-6" : "h-8 w-8"} border-2 border-muted-foreground/20 border-t-emerald-500 rounded-full animate-spin mx-auto ${compacto ? "mb-2" : "mb-3"}`}
      />
      <p className="text-xs text-muted-foreground">{mensaje}</p>
    </div>
  );
}

/**
 * Data-aware wrapper — automatically shows loading, error, or empty states
 * based on the data state. Reduces boilerplate across pages.
 */
interface DataWrapperProps<T> {
  /** The data to display */
  data: T[] | T | null | undefined;
  /** Whether the data is still loading */
  cargando: boolean;
  /** Error from API call */
  error: ApiError | null;
  /** Empty state message */
  mensajeVacio?: string;
  /** Empty state description */
  descripcionVacio?: string;
  /** Icon for empty state */
  iconoVacio?: LucideIcon;
  /** Error title override */
  tituloError?: string;
  /** Retry handler */
  onReintentar?: () => void;
  /** Loading message */
  mensajeCargando?: string;
  /** The content to render when data is available */
  children: (data: NonNullable<T>) => React.ReactNode;
}

export function DataWrapper<T>({
  data,
  cargando,
  error,
  mensajeVacio = "No hay datos disponibles",
  descripcionVacio,
  iconoVacio,
  tituloError,
  onReintentar,
  mensajeCargando,
  children,
}: DataWrapperProps<T>) {
  if (cargando) {
    return <EstadoCargando mensaje={mensajeCargando} />;
  }

  if (error) {
    return (
      <EstadoError
        error={error}
        titulo={tituloError}
        onReintentar={onReintentar}
      />
    );
  }

  // Check if data is empty
  const isEmpty = data == null || (Array.isArray(data) && data.length === 0);

  if (isEmpty) {
    return (
      <EstadoVacio
        icon={iconoVacio}
        titulo={mensajeVacio}
        descripcion={descripcionVacio}
      />
    );
  }

  return <>{children(data as NonNullable<T>)}</>;
}
