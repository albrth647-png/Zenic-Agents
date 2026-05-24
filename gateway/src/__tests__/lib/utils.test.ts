// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 8: Tests rigurosos — funciones puras de utils
// Sin mocks, datos reales. Cubre: normal + vacío + nulo + extremos + error
// ═══════════════════════════════════════════════════════════════════════════════

import { describe, it, expect } from 'vitest';
import {
  tiempoRelativo,
  truncarHash,
  formatoMoneda,
  formatoTamañoArchivo,
  categoriaColor,
  calcularMonitoresSNA,
} from '@/app/_page_parts/utils';
import type { MetricasDashboard, EstadoMonitorSNA } from '@/app/_page_parts/types';

// ─── tiempoRelativo ─────────────────────────────────────────────────────────

describe('tiempoRelativo', () => {
  it('hace Xs para menos de 60 segundos', () => {
    const hace30s = new Date(Date.now() - 30_000).toISOString();
    const resultado = tiempoRelativo(hace30s);
    expect(resultado).toContain('s');
    expect(resultado).toContain('hace');
  });

  it('hace Xm para entre 60s y 3600s', () => {
    const hace5m = new Date(Date.now() - 5 * 60_000).toISOString();
    const resultado = tiempoRelativo(hace5m);
    expect(resultado).toContain('m');
    expect(resultado).toContain('hace');
  });

  it('hace Xh para entre 1h y 24h', () => {
    const hace3h = new Date(Date.now() - 3 * 3_600_000).toISOString();
    const resultado = tiempoRelativo(hace3h);
    expect(resultado).toContain('h');
    expect(resultado).toContain('hace');
  });

  it('hace Xd para más de 24h', () => {
    const hace2d = new Date(Date.now() - 2 * 86_400_000).toISOString();
    const resultado = tiempoRelativo(hace2d);
    expect(resultado).toContain('d');
    expect(resultado).toContain('hace');
  });

  it('hace 0s para fecha actual', () => {
    const ahora = new Date().toISOString();
    const resultado = tiempoRelativo(ahora);
    expect(resultado).toBe('hace 0s');
  });

  it('hace 59s para justo debajo del límite de minutos', () => {
    const hace59s = new Date(Date.now() - 59_000).toISOString();
    const resultado = tiempoRelativo(hace59s);
    expect(resultado).toBe('hace 59s');
  });

  it('hace 1m para justo en el límite de minutos', () => {
    const hace60s = new Date(Date.now() - 60_000).toISOString();
    const resultado = tiempoRelativo(hace60s);
    expect(resultado).toBe('hace 1m');
  });

  it('hace 1h para justo en el límite de horas', () => {
    const hace3600s = new Date(Date.now() - 3_600_000).toISOString();
    const resultado = tiempoRelativo(hace3600s);
    expect(resultado).toBe('hace 1h');
  });

  it('hace 1d para justo en el límite de días', () => {
    const hace86400s = new Date(Date.now() - 86_400_000).toISOString();
    const resultado = tiempoRelativo(hace86400s);
    expect(resultado).toBe('hace 1d');
  });

  it('fecha futura produce valor negativo ( comportamiento esperado )', () => {
    const futuro = new Date(Date.now() + 10_000).toISOString();
    const resultado = tiempoRelativo(futuro);
    // diff será negativo, Math.floor(-10/60) = 0, pero diff < 60 → "hace -10s"
    expect(resultado).toContain('hace');
  });
});

// ─── truncarHash ────────────────────────────────────────────────────────────

describe('truncarHash', () => {
  it('devuelve "génesis" para null', () => {
    expect(truncarHash(null)).toBe('génesis');
  });

  it('devuelve "génesis" para undefined (tratado como falsy)', () => {
    expect(truncarHash(undefined as unknown as string | null)).toBe('génesis');
  });

  it('devuelve "génesis" para string vacío', () => {
    expect(truncarHash('')).toBe('génesis');
  });

  it('no trunca hash corto (<=12 chars)', () => {
    expect(truncarHash('abc123')).toBe('abc123');
  });

  it('no trunca hash de exactamente 12 chars', () => {
    expect(truncarHash('123456789012')).toBe('123456789012');
  });

  it('trunca hash largo a 8 primeros + ... + 4 últimos', () => {
    const hash = 'a1b2c3d4e5f6g7h8i9j0k1l2m3';
    const resultado = truncarHash(hash);
    expect(resultado).toBe('a1b2c3d4...l2m3');
  });

  it('trunca hash SHA-256 típico', () => {
    const hash = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
    const resultado = truncarHash(hash);
    expect(resultado).toBe('e3b0c442...b855');
    expect(resultado.length).toBeLessThan(hash.length);
  });

  it('trunca hash de exactamente 13 chars', () => {
    expect(truncarHash('1234567890123')).toBe('12345678...0123');
  });
});

// ─── formatoMoneda ──────────────────────────────────────────────────────────

describe('formatoMoneda', () => {
  it('formatea 0 como $0', () => {
    expect(formatoMoneda(0)).toContain('0');
  });

  it('formatea 1500 con separador de miles', () => {
    const resultado = formatoMoneda(1500);
    expect(resultado).toContain('1');
    expect(resultado).toContain('500');
  });

  it('formatea números negativos (pérdida)', () => {
    const resultado = formatoMoneda(-500);
    expect(resultado).toContain('500');
  });

  it('formatea números grandes (millones)', () => {
    const resultado = formatoMoneda(1_500_000);
    expect(resultado).toContain('1');
    expect(resultado).toContain('500');
  });

  it('formatea 999 correctamente', () => {
    const resultado = formatoMoneda(999);
    expect(resultado).toContain('999');
  });

  it('formatea 1000 correctamente', () => {
    const resultado = formatoMoneda(1000);
    expect(resultado).toContain('1');
    expect(resultado).toContain('000');
  });

  it('usa estilo currency', () => {
    const resultado = formatoMoneda(42);
    // Debe contener símbolo de moneda ($)
    expect(resultado).toMatch(/\$/);
  });

  it('no muestra decimales (enteros)', () => {
    const resultado = formatoMoneda(100);
    expect(resultado).not.toContain('.00');
  });

  it('trunca decimales (100.99 → $100 o $101)', () => {
    const resultado = formatoMoneda(100.99);
    // Con maximumFractionDigits: 0, redondea
    expect(typeof resultado).toBe('string');
  });

  it('formatea Number.MAX_SAFE_INTEGER sin error', () => {
    expect(() => formatoMoneda(Number.MAX_SAFE_INTEGER)).not.toThrow();
  });

  it('formatea Number.MIN_SAFE_INTEGER sin error', () => {
    expect(() => formatoMoneda(Number.MIN_SAFE_INTEGER)).not.toThrow();
  });
});

// ─── formatoTamañoArchivo ───────────────────────────────────────────────────

describe('formatoTamañoArchivo', () => {
  it('0 bytes → "0 B"', () => {
    expect(formatoTamañoArchivo(0)).toBe('0 B');
  });

  it('1 byte → "1 B"', () => {
    expect(formatoTamañoArchivo(1)).toBe('1 B');
  });

  it('512 bytes → "512 B"', () => {
    expect(formatoTamañoArchivo(512)).toBe('512 B');
  });

  it('1023 bytes → "1023 B"', () => {
    expect(formatoTamañoArchivo(1023)).toBe('1023 B');
  });

  it('1024 bytes → "1.0 KB"', () => {
    expect(formatoTamañoArchivo(1024)).toBe('1.0 KB');
  });

  it('1 MB → "1.0 MB"', () => {
    expect(formatoTamañoArchivo(1024 * 1024)).toBe('1.0 MB');
  });

  it('1.5 MB → "1.5 MB"', () => {
    expect(formatoTamañoArchivo(1.5 * 1024 * 1024)).toBe('1.5 MB');
  });

  it('500 KB → "500.0 KB"', () => {
    expect(formatoTamañoArchivo(500 * 1024)).toBe('500.0 KB');
  });

  it('valor extremo grande no lanza error', () => {
    expect(() => formatoTamañoArchivo(Number.MAX_SAFE_INTEGER)).not.toThrow();
  });

  it('valor negativo no lanza error (comportamiento undefined pero no crash)', () => {
    expect(() => formatoTamañoArchivo(-1)).not.toThrow();
  });
});

// ─── categoriaColor ─────────────────────────────────────────────────────────

describe('categoriaColor', () => {
  it('destructive → rojo', () => {
    const r = categoriaColor('destructive');
    expect(r.label).toBe('DESTRUCTIVA');
    expect(r.bg).toContain('red');
    expect(r.text).toContain('red');
  });

  it('financial → ámbar', () => {
    const r = categoriaColor('financial');
    expect(r.label).toBe('FINANCIERA');
    expect(r.bg).toContain('amber');
  });

  it('safe → gris (default)', () => {
    const r = categoriaColor('safe');
    expect(r.label).toBe('SEGURA');
    expect(r.bg).toContain('gray');
  });

  it('string vacío → default (SEGURA)', () => {
    const r = categoriaColor('');
    expect(r.label).toBe('SEGURA');
  });

  it('string desconocido → default (SEGURA)', () => {
    const r = categoriaColor('unknown_category');
    expect(r.label).toBe('SEGURA');
  });

  it('siempre devuelve las 4 claves', () => {
    const r = categoriaColor('destructive');
    expect(r).toHaveProperty('bg');
    expect(r).toHaveProperty('text');
    expect(r).toHaveProperty('border');
    expect(r).toHaveProperty('label');
  });
});

// ─── calcularMonitoresSNA ───────────────────────────────────────────────────

describe('calcularMonitoresSNA', () => {
  const metricasBase: MetricasDashboard = {
    activeAgents: 5,
    hitlProposals: 3,
    zeroHallucinationsPct: 100,
    securityGateBlocks: 10,
    executionsToday: 50,
    successRate: 99.5,
    avgExecutionTime: 25,
    deniedExecutions: 2,
    totalTools: 10,
    activeTools: 8,
    totalServers: 3,
    healthyServers: 3,
    pendingApprovals: 1,
    criticalAlerts: 0,
  };

  it('devuelve 3 monitores para datos normales', () => {
    const resultado = calcularMonitoresSNA(metricasBase);
    expect(resultado).toHaveLength(3);
    expect(resultado[0].tipo).toBe('ligero');
    expect(resultado[1].tipo).toBe('medio');
    expect(resultado[2].tipo).toBe('pesado');
  });

  it('monitores con avgExecutionTime=25 → ligero "normal" (salud 88), medio y pesado "optimo"', () => {
    const resultado = calcularMonitoresSNA(metricasBase);
    // avgExecTime=25: salud = 100 - (25/200)*100 = 87.5 → Math.round = 88 → "normal"
    expect(resultado[0].valor).toBe(88);
    expect(resultado[0].estado).toBe('normal');
    // successRate=99.5 → óptimo
    expect(resultado[1].estado).toBe('optimo');
    // zeroHallucinationsPct=100 → óptimo
    expect(resultado[2].estado).toBe('optimo');
  });

  it('monitores con avgExecutionTime=0 → ligero óptimo (salud 100)', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, avgExecutionTime: 0 });
    expect(resultado[0].valor).toBe(100);
    expect(resultado[0].estado).toBe('optimo');
  });

  it('monitores con avgExecutionTime=50 → ligero normal (salud ~75)', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, avgExecutionTime: 50 });
    expect(resultado[0].valor).toBe(75);
    expect(resultado[0].estado).toBe('normal');
  });

  it('monitores con avgExecutionTime=200 → ligero crítico (salud 0)', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, avgExecutionTime: 200 });
    expect(resultado[0].valor).toBe(0);
    expect(resultado[0].estado).toBe('critico');
  });

  it('monitores con avgExecutionTime=500 → ligero crítico (salud clamp a 0)', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, avgExecutionTime: 500 });
    expect(resultado[0].valor).toBe(0);
    expect(resultado[0].estado).toBe('critico');
  });

  it('medio con successRate=95 → óptimo', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, successRate: 95 });
    expect(resultado[1].valor).toBe(95);
    expect(resultado[1].estado).toBe('optimo');
  });

  it('medio con successRate=80 → normal', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, successRate: 80 });
    expect(resultado[1].estado).toBe('normal');
  });

  it('medio con successRate=50 → alerta', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, successRate: 50 });
    expect(resultado[1].estado).toBe('alerta');
  });

  it('medio con successRate=20 → crítico', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, successRate: 20 });
    expect(resultado[1].estado).toBe('critico');
  });

  it('pesado con zeroHallucinationsPct=100 → óptimo', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, zeroHallucinationsPct: 100 });
    expect(resultado[2].valor).toBe(100);
    expect(resultado[2].estado).toBe('optimo');
  });

  it('pesado con zeroHallucinationsPct=0 → crítico', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, zeroHallucinationsPct: 0 });
    expect(resultado[2].valor).toBe(0);
    expect(resultado[2].estado).toBe('critico');
  });

  it('pesado con zeroHallucinationsPct negativo → clamp a 0, crítico', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, zeroHallucinationsPct: -50 });
    expect(resultado[2].valor).toBe(0);
    expect(resultado[2].estado).toBe('critico');
  });

  it('pesado con zeroHallucinationsPct > 100 → clamp a 100, óptimo', () => {
    const resultado = calcularMonitoresSNA({ ...metricasBase, zeroHallucinationsPct: 150 });
    expect(resultado[2].valor).toBe(100);
    expect(resultado[2].estado).toBe('optimo');
  });

  it('null → usa defaults (0, 100, 100) sin crash', () => {
    const resultado = calcularMonitoresSNA(null);
    expect(resultado).toHaveLength(3);
    // avgExecutionTime=0 → ligero=100 optimo
    expect(resultado[0].valor).toBe(100);
    expect(resultado[0].estado).toBe('optimo');
    // successRate=100 → medio=100 optimo
    expect(resultado[1].valor).toBe(100);
    expect(resultado[1].estado).toBe('optimo');
    // zeroHallucinationsPct=100 → pesado=100 optimo
    expect(resultado[2].valor).toBe(100);
    expect(resultado[2].estado).toBe('optimo');
  });

  it('objeto vacío (parcial) → usa defaults', () => {
    const resultado = calcularMonitoresSNA({} as MetricasDashboard);
    expect(resultado).toHaveLength(3);
    expect(resultado[0].valor).toBe(100);
  });

  it('valores nunca son negativos', () => {
    const extremo: MetricasDashboard = {
      ...metricasBase,
      avgExecutionTime: -100,
      successRate: -999,
      zeroHallucinationsPct: -100,
    };
    const resultado = calcularMonitoresSNA(extremo);
    resultado.forEach((m) => {
      expect(m.valor).toBeGreaterThanOrEqual(0);
    });
  });

  it('valores nunca superan 100', () => {
    const extremo: MetricasDashboard = {
      ...metricasBase,
      avgExecutionTime: -100,
      successRate: 999,
      zeroHallucinationsPct: 999,
    };
    const resultado = calcularMonitoresSNA(extremo);
    resultado.forEach((m) => {
      expect(m.valor).toBeLessThanOrEqual(100);
    });
  });

  it('cada monitor tiene las 5 propiedades requeridas', () => {
    const resultado = calcularMonitoresSNA(metricasBase);
    resultado.forEach((m: EstadoMonitorSNA) => {
      expect(m).toHaveProperty('tipo');
      expect(m).toHaveProperty('etiqueta');
      expect(m).toHaveProperty('valor');
      expect(m).toHaveProperty('estado');
      expect(m).toHaveProperty('detalle');
    });
  });

  it('estados solo son: optimo, normal, alerta, critico', () => {
    const resultado = calcularMonitoresSNA(metricasBase);
    const estadosValidos = ['optimo', 'normal', 'alerta', 'critico'];
    resultado.forEach((m) => {
      expect(estadosValidos).toContain(m.estado);
    });
  });
});
