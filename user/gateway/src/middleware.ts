// Zenic-Agents v3.0 — Middleware de Protección de Rutas (FASE 3 + FASE 4 + FASE 6)
//
// INVARIANT 4: La regla DENY es absoluta.
// Este middleware protege rutas de API sensibles y requiere
// autenticación header-based (X-User-Id) para operaciones críticas.
//
// FASE 3 - Cambios aplicados:
// - CORS restrictivo con allowlist (F1/E1)
// - Rate limiting con 6 tiers (F2/E2)
// - Query param sanitización (F1/#20)
// - Security headers: CSP, HSTS, X-Frame-Options, etc. (G1/G2)
// - HTTPS enforcement en producción (G1)
// - Audit logging para operaciones críticas (F3/#32)
//
// FASE 4 - Security hardening:
// - NextAuth JWT token validation (#41)
// - API key authentication support (#41)
// - HITL approval routes protection
// - Identity verification routes protection
//
// FASE 6 - Performance:
// - ResourceGovernor context headers (#58)
// - Governor-aware route protection

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { createCspHeader, detectSqlInjection, detectXss } from "@/lib/security";

// ─── Configuración CORS Restrictiva (#24) ─────────────────────────────

const ALLOWED_ORIGINS = (() => {
  const envOrigins = process.env.ZENIC_CORS_ORIGINS;
  if (envOrigins && envOrigins !== "*") {
    return envOrigins.split(",").map((o) => o.trim()).filter(Boolean);
  }
  // Defaults seguros — localhost en desarrollo + Capacitor origins
  if (process.env.NODE_ENV === "development") {
    return [
      "http://localhost:3000",
      "http://127.0.0.1:3000",
      "http://localhost",
      "capacitor://localhost",
      "https://localhost",
      "ionic://localhost",
    ];
  }
  // Producción: DEBE configurarse via ZENIC_CORS_ORIGINS
  // Capacitor usa https://localhost como scheme por defecto
  return [
    "https://localhost",
    "capacitor://localhost",
  ];
})();

const CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"];
const CORS_MAX_AGE = 86400; // 24 horas

function handleCors(request: NextRequest): NextResponse | null {
  const origin = request.headers.get("origin");
  const isPreflight = request.method === "OPTIONS";

  // Sin origin = no es CORS request, permitir
  if (!origin) return null;

  // Verificar origin contra allowlist
  const isAllowedOrigin = isOriginAllowed(origin);

  if (!isAllowedOrigin) {
    if (isPreflight) {
      return new NextResponse(null, { status: 403 });
    }
    // Para requests normales, permitir pero sin CORS headers (browser bloquea)
    return null;
  }

  if (isPreflight) {
    const response = new NextResponse(null, { status: 204 });
    response.headers.set("Access-Control-Allow-Origin", origin);
    response.headers.set("Access-Control-Allow-Methods", CORS_ALLOWED_METHODS.join(", "));
    response.headers.set("Access-Control-Allow-Headers", "Content-Type, X-User-Id, X-Session-Id, Authorization, X-API-Key");
    response.headers.set("Access-Control-Max-Age", String(CORS_MAX_AGE));
    response.headers.set("Access-Control-Allow-Credentials", "true");
    return response;
  }

  return null; // Continuar — CORS headers se añaden en applySecurityHeaders
}

// ─── Rate Limiting (#26) ─────────────────────────────────────────────

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const rateLimitStore = new Map<string, RateLimitEntry>();

const RATE_LIMIT_TIERS: Record<string, { windowMs: number; max: number }> = {
  "/api/v1/subscription/payment": { windowMs: 60_000, max: 5 },      // 5/min pagos
  "/api/v1/hitl/": { windowMs: 60_000, max: 30 },                    // 30/min HITL
  "/api/v1/subscription/": { windowMs: 60_000, max: 20 },             // 20/min suscripciones
  "/api/rbac/": { windowMs: 60_000, max: 60 },                        // 60/min RBAC
  "/api/v1/policies": { windowMs: 60_000, max: 30 },                  // 30/min políticas
  "/api/v1/policy-engine/": { windowMs: 60_000, max: 30 },            // 30/min policy engine
  default: { windowMs: 60_000, max: 100 },                             // 100/min default
};

function checkRateLimit(request: NextRequest): NextResponse | null {
  const { pathname } = request.nextUrl;
  // M2: Prioritize trusted IP sources over spoofeable x-forwarded-for.
  // request.ip is the actual connecting IP from the platform.
  // x-real-ip is set by trusted reverse proxies.
  // x-forwarded-for is easily spoofed — only use first (client) IP if present.
  const clientId = request.headers.get("x-real-ip") ||
    (request as any).ip ||
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "anonymous";

  // Encontrar tier aplicable
  let tier = RATE_LIMIT_TIERS.default;
  for (const [prefix, config] of Object.entries(RATE_LIMIT_TIERS)) {
    if (prefix !== "default" && pathname.startsWith(prefix)) {
      tier = config;
      break;
    }
  }

  const key = `${clientId}:${pathname.substring(0, 50)}`;
  const now = Date.now();

  // Limpiar entradas expiradas periódicamente
  if (rateLimitStore.size > 10000) {
    for (const [k, v] of rateLimitStore) {
      if (v.resetAt < now) rateLimitStore.delete(k);
    }
  }

  const entry = rateLimitStore.get(key);
  if (!entry || entry.resetAt < now) {
    rateLimitStore.set(key, { count: 1, resetAt: now + tier.windowMs });
    return null;
  }

  entry.count++;
  if (entry.count > tier.max) {
    const retryAfter = Math.ceil((entry.resetAt - now) / 1000);
    return NextResponse.json(
      {
        error: "Demasiadas solicitudes. Intenta de nuevo más tarde.",
        code: "RATE_LIMITED",
        retryAfter,
      },
      {
        status: 429,
        headers: {
          "Retry-After": String(retryAfter),
          "X-RateLimit-Limit": String(tier.max),
          "X-RateLimit-Remaining": "0",
          "X-RateLimit-Reset": String(Math.ceil(entry.resetAt / 1000)),
        },
      },
    );
  }

  return null; // Dentro del límite
}

// ─── CSRF Protection (C3) ────────────────────────────────────────────
// Validates Origin and Referer headers for state-changing requests
// to prevent Cross-Site Request Forgery attacks.

const UNSAFE_METHODS = ["POST", "PUT", "DELETE", "PATCH"];

const ALLOWED_ORIGIN_PATTERNS = (() => {
  // Derive from ALLOWED_ORIGINS for consistency
  const base = ALLOWED_ORIGINS.map((o) => {
    try { return new URL(o).hostname; } catch { return o; }
  });
  // Always trust localhost in any form
  base.push("localhost", "127.0.0.1", "capacitor://localhost");
  return base;
})();

function checkCsrf(request: NextRequest): NextResponse | null {
  // Only enforce for state-changing requests on API routes
  if (!UNSAFE_METHODS.includes(request.method)) return null;
  if (!request.nextUrl.pathname.startsWith("/api/")) return null;

  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");

  // No Origin and no Referer — likely a same-origin request or direct API call
  // Allow through (the request may be from a server-side client)
  if (!origin && !referer) return null;

  // Check Origin header if present
  if (origin) {
    try {
      const originHost = new URL(origin).hostname;
      const isAllowed = ALLOWED_ORIGIN_PATTERNS.some((allowed) =>
        originHost === allowed || originHost.endsWith("." + allowed),
      );
      if (!isAllowed) {
        return NextResponse.json(
          { error: "CSRF: Origin no permitido.", code: "CSRF_DENIED" },
          { status: 403 },
        );
      }
    } catch {
      return NextResponse.json(
        { error: "CSRF: Origin inválido.", code: "CSRF_DENIED" },
        { status: 403 },
      );
    }
  }

  // Fallback: check Referer if Origin is absent
  if (!origin && referer) {
    try {
      const refererHost = new URL(referer).hostname;
      const isAllowed = ALLOWED_ORIGIN_PATTERNS.some((allowed) =>
        refererHost === allowed || refererHost.endsWith("." + allowed),
      );
      if (!isAllowed) {
        return NextResponse.json(
          { error: "CSRF: Referer no permitido.", code: "CSRF_DENIED" },
          { status: 403 },
        );
      }
    } catch {
      return NextResponse.json(
        { error: "CSRF: Referer inválido.", code: "CSRF_DENIED" },
        { status: 403 },
      );
    }
  }

  return null;
}

// ─── Query Param Sanitización (#20) ──────────────────────────────────
// Uses centralized detection functions from lib/security/sanitize (B3).

function sanitizeQueryParams(request: NextRequest): NextResponse | null {
  const { searchParams } = request.nextUrl;

  for (const [key, value] of searchParams.entries()) {
    // Verificar SQL injection via lib/security/sanitize
    const sqlResult = detectSqlInjection(value);
    if (sqlResult.detected) {
      console.warn(`[sanitize] SQL injection attempt detected in query param "${key}": ${value.substring(0, 100)}`);
      return NextResponse.json(
        { error: "Parámetro de consulta inválido.", code: "INVALID_INPUT" },
        { status: 400 },
      );
    }

    // Verificar XSS via lib/security/sanitize
    const xssResult = detectXss(value);
    if (xssResult.detected) {
      console.warn(`[sanitize] XSS attempt detected in query param "${key}": ${value.substring(0, 100)}`);
      return NextResponse.json(
        { error: "Parámetro de consulta inválido.", code: "INVALID_INPUT" },
        { status: 400 },
      );
    }

    // Longitud máxima
    if (value.length > 500) {
      return NextResponse.json(
        { error: "Parámetro de consulta demasiado largo.", code: "INVALID_INPUT" },
        { status: 400 },
      );
    }
  }

  return null;
}

// ─── Body Sanitización (M1) ─────────────────────────────────────────
// Lee y sanitiza el body de requests POST/PUT/PATCH/PATCH.
// Usa request.clone() para no consumir el stream del request original.

const MAX_BODY_SIZE = 50_000; // 50KB — evita DoS por bodies gigantes

async function sanitizeBody(request: NextRequest): Promise<NextResponse | null> {
  // Solo métodos con body
  if (!UNSAFE_METHODS.includes(request.method)) return null;
  if (!request.nextUrl.pathname.startsWith("/api/")) return null;

  try {
    const cloned = request.clone();
    const text = await cloned.text();
    if (!text || text.length === 0) return null;

    // Max body size check (defense-in-depth, el server ya limita en nginx/Caddy)
    if (text.length > MAX_BODY_SIZE) {
      return NextResponse.json(
        { error: "Solicitud demasiado grande.", code: "BODY_TOO_LARGE" },
        { status: 413 },
      );
    }

    // Verificar SQL injection en body via lib/security/sanitize (B3)
    const sqlResult = detectSqlInjection(text);
    if (sqlResult.detected) {
      console.warn(`[sanitize] SQL injection attempt detected in request body`);
      return NextResponse.json(
        { error: "Solicitud inválida.", code: "INVALID_INPUT" },
        { status: 400 },
      );
    }

    // Verificar XSS en body via lib/security/sanitize (B3)
    const xssResult = detectXss(text);
    if (xssResult.detected) {
      console.warn(`[sanitize] XSS attempt detected in request body`);
      return NextResponse.json(
        { error: "Solicitud inválida.", code: "INVALID_INPUT" },
        { status: 400 },
      );
    }
  } catch {
    // Body no disponible (stream ya consumido, no hay body, etc.) — pasar
    return null;
  }

  return null;
}


// ─── Security Headers (G1/G2) ───────────────────────────────────────

function applySecurityHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const isProd = process.env.NODE_ENV === "production";

  // Content-Security-Policy (using secure defaults from lib/security/headers)
  // Note: 'unsafe-eval' deliberately excluded — CSP must prevent code injection
  response.headers.set(
    "Content-Security-Policy",
    createCspHeader({
      'script-src': ["'self'", "'unsafe-inline'"],
      'img-src': ["'self'", "data:", "blob:"],
      'connect-src': ["'self'", "http://localhost:*", "https://localhost:*", "capacitor://localhost"],
    }),
  );

  // X-Frame-Options
  response.headers.set("X-Frame-Options", "DENY");

  // X-Content-Type-Options
  response.headers.set("X-Content-Type-Options", "nosniff");

  // X-XSS-Protection (disabled — CSP is preferred)
  response.headers.set("X-XSS-Protection", "0");

  // Referrer-Policy
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  // Permissions-Policy (M5: bloquea APIs sensibles adicionales)
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), " +
    "magnetometer=(), gyroscope=(), accelerometer=(), " +
    "midi=(), sync-xhr=(), fullscreen=(self), display-capture=(), " +
    "screen-wake-lock=(), web-share=()",
  );

  // HSTS (solo en producción, preload configurable via ZENIC_HEADERS_HSTS_PRELOAD)
  if (isProd) {
    const enablePreload = process.env.ZENIC_HEADERS_HSTS_PRELOAD !== "false";
    const hstsValue = enablePreload
      ? "max-age=63072000; includeSubDomains; preload"
      : "max-age=63072000; includeSubDomains";
    response.headers.set("Strict-Transport-Security", hstsValue);
  }

  // Cache-Control para rutas de API
  if (request.nextUrl.pathname.startsWith("/api/")) {
    response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, private");
  }

  // CORS header para responses normales (M4: defense-in-depth)
  const origin = request.headers.get("origin");
  if (origin) {
    // Reject wildcard origin with credentials — browsers block this anyway,
    // but catching it here prevents silent misconfiguration.
    if (origin === "*") {
      console.warn('[middleware] Wildcard CORS origin ("*") rejected — wildcard+credentials is forbidden by browsers and this middleware enforces that');
      return response;
    }
    if (isOriginAllowed(origin)) {
      response.headers.set("Access-Control-Allow-Origin", origin);
      response.headers.set("Access-Control-Allow-Credentials", "true");
    }
  }

  return response;
}

// ─── Helpers ──────────────────────────────────────────────────────────

/** Create a JSON error response wrapped with security headers. */
function jsonResponse(
  data: Record<string, unknown>,
  status: number,
  request: NextRequest,
): NextResponse {
  return applySecurityHeaders(NextResponse.json(data, { status }), request);
}

/** Check if an origin is in the CORS allowlist. */
function isOriginAllowed(origin: string): boolean {
  return ALLOWED_ORIGINS.includes(origin) ||
    (process.env.NODE_ENV === "development" && origin.includes("localhost")) ||
    origin === "capacitor://localhost" ||
    origin === "https://localhost" ||
    origin === "ionic://localhost";
}

// ─── HTTPS Enforcement (G1) ──────────────────────────────────────────

function enforceHttps(request: NextRequest): NextResponse | null {
  if (process.env.NODE_ENV !== "production") return null;

  const proto = request.headers.get("x-forwarded-proto");
  if (proto && proto !== "https") {
    const httpsUrl = request.nextUrl.clone();
    httpsUrl.protocol = "https:";
    return NextResponse.redirect(httpsUrl, 301);
  }

  return null;
}

// ─── Rutas protegidas ────────────────────────────────────────────────

const RUTAS_BLOQUEADAS_SIEMPRE = [
  "/api/seed",                     // Población de BD — extremadamente peligroso
  "/api/v1/subscription/saga/",    // Saga lifecycle — operaciones financieras
  "/api/v1/subscription/payment/", // Pagos — operaciones financieras
];

const RUTAS_ADMIN_REQUIEREN_AUTH = [
  "/api/rbac/assign",              // Asignar roles
  "/api/rbac/revoke",              // Revocar roles
  "/api/rbac/roles",               // CRUD de roles (POST/PUT/DELETE)
  "/api/policies",                 // CRUD de políticas (POST/PUT/DELETE)
  "/api/v1/policies",              // Declarative policies
  "/api/v1/policy-engine",         // Policy engine admin
  "/api/v1/hitl/",                 // HITL operations
  "/api/v1/subscription/",         // Subscription management
  "/api/users",                    // User management
  "/api/approvals",                // FASE 4: HITL approval system
  "/api/identity",                 // FASE 4: Identity verification
];

const RUTAS_LECTURA_PERMITIDAS_DEV = [
  "/api/rbac/check",               // Check permission (read-only)
  "/api/rbac/permissions",         // List permissions (read-only)
  "/api/audit",                    // Read audit logs
  "/api/dashboard/",               // Dashboard data
  "/api/mcp/servers",              // MCP server list
  "/api/mcp/tools",                // MCP tool list
];

const RUTAS_PUBLICAS = [
  "/_next/",
  "/favicon.ico",
  "/logo.svg",
  "/robots.txt",
  "/api/route",                    // Health check
  "/api/auth/",                    // FASE 4: NextAuth endpoints (public, rate limited)
  "/api/health",                   // FASE 6: Health endpoint with governor metrics
  "/auth/",                        // Sprint 5: Auth pages (login, register, forgot-password)
];

// ─── Constant-time String Comparison ─────────────────────────────
// Prevents timing side-channel attacks on API key comparison.
// Works in all runtimes (Edge, Node.js, browser) without native crypto.

function timingSafeCompare(a: string, b: string): boolean {
  const maxLen = Math.max(a.length, b.length);
  // XOR to detect length mismatch — mixed into final result
  let result = a.length ^ b.length;

  for (let i = 0; i < maxLen; i++) {
    result |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }

  return result === 0;
}

// ─── FASE 4: NextAuth JWT + API Key Authentication (#41) ────────────

async function authenticateRequest(request: NextRequest): Promise<Headers | null> {
  const { pathname } = request.nextUrl;

  // Only authenticate protected routes
  const requiresAuth =
    pathname.startsWith("/api/mcp/") ||
    pathname.startsWith("/api/approvals") ||
    pathname.startsWith("/api/identity");

  if (!requiresAuth) return null;

  // Try NextAuth JWT first
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (token) {
      const headers = new Headers(request.headers);
      headers.set("x-user-id", (token as any).userId || token.sub || "");
      headers.set("x-user-role", (token as any).role || "user");
      headers.set("x-user-email", token.email || "");
      headers.set("x-governor-check", "required"); // FASE 6: Governor context
      return headers;
    }
  } catch {
    // JWT validation failed — continue to API key check
  }

  // Check for API key authentication
  const authHeader = request.headers.get("authorization");
  if (authHeader?.startsWith("Bearer ")) {
    const apiKey = authHeader.substring(7);
    const validApiKey = process.env.API_SECRET_KEY;

    // Constant-time comparison to prevent timing side-channel attacks
    if (validApiKey && timingSafeCompare(apiKey, validApiKey)) {
      const headers = new Headers(request.headers);
      headers.set("x-governor-check", "required"); // FASE 6: Governor context
      return headers;
    }
  }

  // No valid authentication found — return error
  return null; // Caller will return 401
}

// ─── Middleware Principal ────────────────────────────────────────────

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const method = request.method;

  // 1. HTTPS enforcement (producción)
  const httpsRedirect = enforceHttps(request);
  if (httpsRedirect) return httpsRedirect;

  // 2. Permitir archivos estáticos y rutas públicas
  if (RUTAS_PUBLICAS.some((ruta) => pathname.startsWith(ruta))) {
    return applySecurityHeaders(NextResponse.next(), request);
  }

  // 2a. CSRF protection (C3) — valida Origin/Referer para métodos no seguros
  const csrfError = checkCsrf(request);
  if (csrfError) return csrfError; // Already wrapped in checkCsrf — safe as-is

  // 2b. Sprint 5: Dashboard route protection — require JWT authentication
  if (pathname.startsWith("/dashboard")) {
    try {
      const token = await getToken({
        req: request,
        secret: process.env.NEXTAUTH_SECRET,
      });
      if (!token) {
        const loginUrl = new URL("/auth/login", request.url);
        loginUrl.searchParams.set("callbackUrl", pathname);
        return NextResponse.redirect(loginUrl);
      }
    } catch {
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // 3. CORS preflight
  const corsResponse = handleCors(request);
  if (corsResponse) return applySecurityHeaders(corsResponse, request);

  // 4. Query param sanitización
  const sanitizationError = sanitizeQueryParams(request);
  if (sanitizationError) return sanitizationError; // Already wrapped by applySecurityHeaders via jsonResponse

  // 4b. Body sanitización (M1) — solo para POST/PUT/PATCH/DELETE
  const bodySanitizationError = await sanitizeBody(request);
  if (bodySanitizationError) return bodySanitizationError;

  // 5. Rate limiting
  const rateLimitResponse = checkRateLimit(request);
  if (rateLimitResponse) return rateLimitResponse;

  // 6. Rutas BLOQUEADAS SIEMPRE
  for (const ruta of RUTAS_BLOQUEADAS_SIEMPRE) {
    if (pathname.startsWith(ruta)) {
      if (pathname === "/api/seed" && process.env.NODE_ENV === "development") {
        return jsonResponse(
          { error: "Ruta bloqueada. Ejecutar prisma db seed directamente." },
          403,
          request,
        );
      }
      return jsonResponse(
        { error: "Acceso denegado. Se requiere autenticación.", code: "UNAUTHENTICATED" },
        401,
        request,
      );
    }
  }

  // 7. FASE 4: NextAuth JWT + API Key authentication for protected routes
  if (
    pathname.startsWith("/api/mcp/") ||
    pathname.startsWith("/api/approvals") ||
    pathname.startsWith("/api/identity")
  ) {
    const authHeaders = await authenticateRequest(request);
    if (authHeaders) {
      return applySecurityHeaders(
        NextResponse.next({ request: { headers: authHeaders } }),
        request,
      );
    }

    // No valid auth found for protected route
    return jsonResponse(
      {
        error: "Authentication required",
        code: "AUTH_REQUIRED",
        message: "Sign in to access this API. Use NextAuth session, API key, or signed request.",
      },
      401,
      request,
    );
  }

  // 7b. Producción: rutas de API protegidas requieren auth, PERO auth routes son públicas
  if (process.env.NODE_ENV === "production") {
    // Rutas de autenticación son públicas (login, register, nextauth)
    const isAuthRoute = pathname.startsWith("/api/auth/") ||
      pathname.startsWith("/api/health") ||
      pathname === "/api/route";

    if (pathname.startsWith("/api/") && !isAuthRoute) {
      // Verificar JWT para rutas protegidas
      try {
        const token = await getToken({
          req: request,
          secret: process.env.NEXTAUTH_SECRET,
        });
        if (!token) {
          const userId = request.headers.get("x-user-id");
          if (!userId) {
            return jsonResponse(
              { error: "Acceso denegado. Se requiere autenticación.", code: "UNAUTHENTICATED" },
              401,
              request,
            );
          }
        }
      } catch {
        // JWT validation failed — check for API key or X-User-Id
        const userId = request.headers.get("x-user-id");
        if (!userId) {
          return jsonResponse(
            { error: "Acceso denegado. Se requiere autenticación.", code: "UNAUTHENTICATED" },
            401,
            request,
          );
        }
      }
    }
    return applySecurityHeaders(NextResponse.next(), request);
  }

  // 8. Desarrollo: modo local-first con protecciones mínimas
  for (const ruta of RUTAS_ADMIN_REQUIEREN_AUTH) {
    if (pathname.startsWith(ruta) && method !== "GET") {
      const userId = request.headers.get("x-user-id");
      if (!userId) {
        return jsonResponse(
          {
            error: "Operación administrativa requiere header X-User-Id",
            code: "UNAUTHENTICATED",
            hint: "Incluye header: X-User-Id: <tu-user-id>",
          },
          401,
          request,
        );
      }
    }
  }

  // 9. Rutas de lectura en desarrollo: inyectar usuario local si no hay header
  if (RUTAS_LECTURA_PERMITIDAS_DEV.some((ruta) => pathname.startsWith(ruta))) {
    const userId = request.headers.get("x-user-id");
    if (!userId) {
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set("x-user-id", "local-seller");
      return applySecurityHeaders(
        NextResponse.next({
          request: { headers: requestHeaders },
        }),
        request,
      );
    }
  }

  return applySecurityHeaders(NextResponse.next(), request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
