import '@testing-library/jest-dom/vitest';

// ═══════════════════════════════════════════════════════════════════════════════
// Polyfills para jsdom — NO son mocks, son implementaciones reales mínimas
// que jsdom no provee pero que el navegador sí tiene
// ═══════════════════════════════════════════════════════════════════════════════

// Polyfill: window.matchMedia (requerido por next-themes y use-mobile)
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// Polyfill: EventSource (requerido por useRealtimeEvents)
// Implementación real mínima que jsdom no tiene
if (typeof globalThis.EventSource === 'undefined') {
  class EventSourcePolyfill {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;
    readonly CONNECTING = 0;
    readonly OPEN = 1;
    readonly CLOSED = 2;
    url: string;
    readyState: number = 0;
    onopen: ((this: EventSource, ev: Event) => any) | null = null;
    onmessage: ((this: EventSource, ev: MessageEvent) => any) | null = null;
    onerror: ((this: EventSource, ev: Event) => any) | null = null;

    constructor(url: string) {
      this.url = url;
      this.readyState = 0;
      // No simulamos conexión automática para evitar efectos secundarios
      // en tests. El test que necesite simular conexión lo hará manualmente.
    }

    close() {
      this.readyState = 2;
    }

    addEventListener() {}
    removeEventListener() {}
    dispatchEvent() { return true; }
  }

  globalThis.EventSource = EventSourcePolyfill as unknown as typeof EventSource;
}
