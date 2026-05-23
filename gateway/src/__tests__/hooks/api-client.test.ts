import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  apiFetch,
  apiFetchParallel,
  formatApiError,
  apiPost,
  apiPut,
  apiDelete,
} from '@/lib/api-client';
import type { ApiError } from '@/lib/api-client';

// ─── apiFetch — cliente HTTP centralizado ───────────────────────────

describe('apiFetch', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('retorna JSON parseado en caso de éxito', async () => {
    const mockData = { id: 1, name: 'Zenic' };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    }));

    const result = await apiFetch('/api/test');
    expect(result).toEqual(mockData);
  });

  it('lanza ApiError con status correcto en error HTTP', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({ error: 'Recurso no encontrado' }),
    }));

    try {
      await apiFetch('/api/test');
      expect.fail('Debería haber lanzado un error');
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.message).toBe('Recurso no encontrado');
    }
  });

  it('lanza ApiError con code NETWORK_ERROR en error de red', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    try {
      await apiFetch('/api/test');
      expect.fail('Debería haber lanzado un error');
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.code).toBe('NETWORK_ERROR');
      expect(apiErr.status).toBe(0);
      expect(apiErr.message).toContain('No se pudo conectar');
    }
  });

  it('lanza ApiError con code TIMEOUT en abort por timeout', async () => {
    const abortError = new DOMException('The operation was aborted', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError));

    try {
      await apiFetch('/api/test', { timeout: 1 });
      expect.fail('Debería haber lanzado un error');
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.code).toBe('TIMEOUT');
      expect(apiErr.status).toBe(408);
      expect(apiErr.message).toContain('expiró');
    }
  });

  it('usa errorMessage personalizado cuando se proporciona', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({}),
    }));

    try {
      await apiFetch('/api/test', { errorMessage: 'Error custom' });
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.message).toBe('Error custom');
    }
  });

  it('maneja respuesta de error sin JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: () => Promise.reject(new Error('No JSON')),
    }));

    try {
      await apiFetch('/api/test');
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(503);
      expect(apiErr.message).toContain('503');
    }
  });
});

// ─── apiFetchParallel — fetch paralelo con aislamiento de errores ───

describe('apiFetchParallel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('maneja éxito y fracaso mixto por endpoint', async () => {
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ name: 'success' }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        json: () => Promise.resolve({ error: 'fallo' }),
      });
    }));

    const result = await apiFetchParallel<{ a: { name: string }; b: never }>({
      a: '/api/success',
      b: '/api/fail',
    });

    expect(result.data.a).toEqual({ name: 'success' });
    expect(result.errors.a).toBeNull();
    expect(result.data.b).toBeNull();
    expect(result.errors.b).not.toBeNull();
    expect(result.errors.b!.status).toBe(500);
  });

  it('retorna éxito para todos cuando todos funcionan', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    }));

    const result = await apiFetchParallel<{ x: { ok: boolean }; y: { ok: boolean } }>({
      x: '/api/x',
      y: '/api/y',
    });

    expect(result.data.x).toEqual({ ok: true });
    expect(result.data.y).toEqual({ ok: true });
    expect(result.errors.x).toBeNull();
    expect(result.errors.y).toBeNull();
  });
});

// ─── formatApiError — mensajes amigables por código de estado ────────

describe('formatApiError', () => {
  it('retorna cadena vacía para error nulo', () => {
    expect(formatApiError(null)).toBe('');
  });

  it('retorna mensaje para status 0 (sin conexión)', () => {
    expect(formatApiError({ message: 'x', status: 0 })).toContain('Sin conexión');
  });

  it('retorna mensaje para 401 (sesión expirada)', () => {
    expect(formatApiError({ message: 'x', status: 401 })).toContain('Sesión expirada');
  });

  it('retorna mensaje para 403 (sin permisos)', () => {
    expect(formatApiError({ message: 'x', status: 403 })).toContain('No tienes permisos');
  });

  it('retorna mensaje para 404 (recurso no encontrado)', () => {
    expect(formatApiError({ message: 'x', status: 404 })).toContain('no encontrado');
  });

  it('retorna mensaje para 429 (demasiadas solicitudes)', () => {
    expect(formatApiError({ message: 'x', status: 429 })).toContain('Demasiadas solicitudes');
  });

  it('retorna mensaje para 5xx (error del servidor)', () => {
    expect(formatApiError({ message: 'x', status: 500 })).toContain('Error del servidor');
    expect(formatApiError({ message: 'x', status: 502 })).toContain('Error del servidor');
    expect(formatApiError({ message: 'x', status: 503 })).toContain('Error del servidor');
  });

  it('retorna mensaje genérico para otros códigos', () => {
    expect(formatApiError({ message: 'Algo pasó', status: 418 })).toBe('Algo pasó');
  });
});

// ─── Métodos de conveniencia: apiPost, apiPut, apiDelete ─────────────

describe('métodos de conveniencia HTTP', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('apiPost envía POST con Content-Type JSON', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ created: true }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await apiPost('/api/test', { name: 'test' });
    expect(result).toEqual({ created: true });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
  });

  it('apiPut envía PUT con Content-Type JSON', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ updated: true }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await apiPut('/api/test', { name: 'test' });
    expect(result).toEqual({ updated: true });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
  });

  it('apiDelete envía DELETE', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deleted: true }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await apiDelete('/api/test');
    expect(result).toEqual({ deleted: true });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});
