import { describe, it, expect, vi, beforeEach } from 'vitest';
import { swrFetcher, defaultSWRConfig } from '@/lib/swr-config';

// ─── swrFetcher — fetcher para SWR ──────────────────────────────────

describe('swrFetcher', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('llama apiFetch con la URL proporcionada', async () => {
    const mockData = { items: [1, 2, 3] };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    }));

    const result = await swrFetcher('/api/dashboard/metrics');
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/dashboard/metrics',
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      })
    );
  });

  it('propaga errores de apiFetch', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: () => Promise.resolve({ error: 'No auth' }),
    }));

    await expect(swrFetcher('/api/test')).rejects.toEqual(
      expect.objectContaining({ status: 401 })
    );
  });
});

// ─── defaultSWRConfig.shouldRetryOnError ─────────────────────────────

describe('defaultSWRConfig.shouldRetryOnError', () => {
  const shouldRetry = defaultSWRConfig.shouldRetryOnError as (err: unknown) => boolean;

  it('retorna false para errores 4xx (no reintentar)', () => {
    expect(shouldRetry({ status: 400, message: 'Bad Request' })).toBe(false);
    expect(shouldRetry({ status: 401, message: 'Unauthorized' })).toBe(false);
    expect(shouldRetry({ status: 403, message: 'Forbidden' })).toBe(false);
    expect(shouldRetry({ status: 404, message: 'Not Found' })).toBe(false);
    expect(shouldRetry({ status: 429, message: 'Too Many Requests' })).toBe(false);
  });

  it('retorna true para errores 5xx (reintentar)', () => {
    expect(shouldRetry({ status: 500, message: 'Internal Server Error' })).toBe(true);
    expect(shouldRetry({ status: 502, message: 'Bad Gateway' })).toBe(true);
    expect(shouldRetry({ status: 503, message: 'Service Unavailable' })).toBe(true);
  });

  it('retorna true para errores desconocidos (sin status)', () => {
    expect(shouldRetry(new Error('Network error'))).toBe(true);
    expect(shouldRetry(null)).toBe(true);
    expect(shouldRetry('string error')).toBe(true);
    expect(shouldRetry(undefined)).toBe(true);
  });
});

// ─── defaultSWRConfig — configuración general ────────────────────────

describe('defaultSWRConfig — configuración general', () => {
  it('tiene fetcher definido', () => {
    expect(defaultSWRConfig.fetcher).toBeDefined();
    expect(typeof defaultSWRConfig.fetcher).toBe('function');
  });

  it('no revalida al foco por defecto', () => {
    expect(defaultSWRConfig.revalidateOnFocus).toBe(false);
  });

  it('revalida al reconectar', () => {
    expect(defaultSWRConfig.revalidateOnReconnect).toBe(true);
  });

  it('tiene errorRetryCount limitado a 2', () => {
    expect(defaultSWRConfig.errorRetryCount).toBe(2);
  });

  it('tiene dedupingInterval de 5 segundos', () => {
    expect(defaultSWRConfig.dedupingInterval).toBe(5000);
  });
});
