// ═══════════════════════════════════════════════════════════════════════════════
// Zenic-Agents v3 — Centralized API Client with Error Handling
// Sprint 6: Replaces raw fetch() calls with typed, error-aware client
// ═══════════════════════════════════════════════════════════════════════════════

/** Error structure returned by Zenic API routes */
export interface ApiError {
  message: string;
  code?: string;
  status: number;
}

/** Standardized API response wrapper */
export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
}

/** Options for the API client */
export interface FetchOptions extends RequestInit {
  /** Custom error message override */
  errorMessage?: string;
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

/**
 * Typed fetch wrapper with timeout, error handling, and response parsing.
 * Returns parsed JSON on success, throws ApiError on failure.
 */
export async function apiFetch<T>(
  url: string,
  options: FetchOptions = {}
): Promise<T> {
  const { errorMessage, timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Merge the abort signal with any user-provided signal
  const signal = fetchOptions.signal
    ? AbortSignal.any([controller.signal, fetchOptions.signal])
    : controller.signal;

  try {
    const res = await fetch(url, { ...fetchOptions, signal });

    if (!res.ok) {
      let errorBody: { error?: string; code?: string; message?: string } = {};
      try {
        errorBody = await res.json();
      } catch {
        // Non-JSON error response
      }

      const apiError: ApiError = {
        message:
          errorMessage ||
          errorBody.error ||
          errorBody.message ||
          `Error ${res.status}: ${res.statusText}`,
        code: errorBody.code,
        status: res.status,
      };

      throw apiError;
    }

    return (await res.json()) as T;
  } catch (err: any) {
    // Re-throw ApiError as-is
    if (err && typeof err === "object" && "status" in err) {
      throw err;
    }

    // Convert other errors to ApiError
    if (err?.name === "AbortError") {
      const apiError: ApiError = {
        message: errorMessage || "La solicitud expiró. Intenta de nuevo.",
        code: "TIMEOUT",
        status: 408,
      };
      throw apiError;
    }

    const apiError: ApiError = {
      message:
        errorMessage || "No se pudo conectar con el servidor. Verifica tu conexión.",
      code: "NETWORK_ERROR",
      status: 0,
    };
    throw apiError;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Fetch multiple endpoints in parallel with individual error isolation.
 * Each endpoint succeeds or fails independently — a single failure doesn't
 * affect the others. This replaces the old Promise.allSettled + swallow pattern.
 */
export async function apiFetchParallel<T extends Record<string, unknown>>(
  endpoints: { [K in keyof T]: string },
  options?: FetchOptions
): Promise<{
  data: { [K in keyof T]: T[K] | null };
  errors: { [K in keyof T]: ApiError | null };
}> {
  const keys = Object.keys(endpoints) as Array<keyof T>;
  const results = await Promise.allSettled(
    keys.map((key) => apiFetch<T[keyof T]>(endpoints[key] as string, options))
  );

  const data = {} as { [K in keyof T]: T[K] | null };
  const errors = {} as { [K in keyof T]: ApiError | null };

  keys.forEach((key, idx) => {
    const result = results[idx];
    if (result.status === "fulfilled") {
      data[key] = result.value;
      errors[key] = null;
    } else {
      data[key] = null;
      errors[key] =
        result.reason && typeof result.reason === "object" && "status" in result.reason
          ? (result.reason as ApiError)
          : {
              message: "Error desconocido al cargar datos",
              code: "UNKNOWN",
              status: 500,
            };
    }
  });

  return { data, errors };
}

/**
 * Convenience: POST JSON with auto content-type header.
 */
export async function apiPost<T>(
  url: string,
  body: unknown,
  options?: FetchOptions
): Promise<T> {
  return apiFetch<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...options?.headers },
    body: JSON.stringify(body),
    ...options,
  });
}

/**
 * Convenience: PUT JSON with auto content-type header.
 */
export async function apiPut<T>(
  url: string,
  body: unknown,
  options?: FetchOptions
): Promise<T> {
  return apiFetch<T>(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...options?.headers },
    body: JSON.stringify(body),
    ...options,
  });
}

/**
 * Convenience: DELETE request.
 */
export async function apiDelete<T>(
  url: string,
  options?: FetchOptions
): Promise<T> {
  return apiFetch<T>(url, {
    method: "DELETE",
    ...options,
  });
}

/** Format an ApiError into a user-friendly display string */
export function formatApiError(error: ApiError | null): string {
  if (!error) return "";
  if (error.status === 0) return "Sin conexión al servidor";
  if (error.status === 401) return "Sesión expirada. Inicia sesión de nuevo.";
  if (error.status === 403) return "No tienes permisos para esta acción.";
  if (error.status === 404) return "Recurso no encontrado.";
  if (error.status === 408) return "La solicitud tardó demasiado. Intenta de nuevo.";
  if (error.status === 429) return "Demasiadas solicitudes. Espera un momento.";
  if (error.status >= 500) return "Error del servidor. Intenta más tarde.";
  return error.message;
}
