import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

// ─── Phase 6.1: Custom ESLint rule for API auth enforcement ────────
import apiAuthRequired from "./eslint-rules/api-auth-required.js";

const eslintConfig = [...nextCoreWebVitals, ...nextTypescript, {
  rules: {
    // ─── TypeScript: REGLAS ACTIVAS ─────────────────────────────────
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": ["warn", {
      argsIgnorePattern: "^_",
      varsIgnorePattern: "^_",
    }],
    "@typescript-eslint/no-non-null-assertion": "warn",
    "@typescript-eslint/ban-ts-comment": "warn",
    "@typescript-eslint/prefer-as-const": "warn",
    // no-unused-disable-directive removed — not available in this eslint/typescript-eslint version

    // ─── React: REGLAS ACTIVAS ──────────────────────────────────────
    // CRÍTICO: Esta regla detecta closures stale y bugs de estado.
    // Si genera warnings falsos, usar la directiva:
    // // eslint-disable-next-line react-hooks/exhaustive-deps
    // con comentario explicando por qué.
    "react-hooks/exhaustive-deps": "warn",
    "react-hooks/purity": "warn",
    "react/no-unescaped-entities": "off",
    "react/display-name": "off",
    "react/prop-types": "off",
    "react-compiler/react-compiler": "off",

    // ─── Next.js: REGLAS ACTIVAS ────────────────────────────────────
    "@next/next/no-img-element": "warn",
    "@next/next/no-html-link-for-pages": "off",

    // ─── General: REGLAS ACTIVAS ────────────────────────────────────
    "prefer-const": "warn",
    "no-unused-vars": "off",
    // Phase 6.2: no-console upgraded from warn → error for production code.
    // console.warn and console.error are still allowed.
    // Use createRedactedLogger from @/lib/security/log-redact instead.
    "no-console": ["error", { allow: ["warn", "error"] }],
    "no-debugger": "error",
    "no-empty": "warn",
    "no-irregular-whitespace": "warn",
    "no-case-declarations": "off",
    "no-fallthrough": "warn",
    "no-mixed-spaces-and-tabs": "error",
    "no-redeclare": "error",
    "no-undef": "off",
    "no-unreachable": "warn",
    "no-useless-escape": "warn",
  },
}, {
  // ─── Phase 6.1: Custom API Auth Rule ──────────────────────────────
  // This local plugin enforces that all API route handlers call an
  // authentication function before processing requests. Prevents the
  // reintroduction of unauthenticated endpoints (Phase 0 vulnerability).
  //
  // Severity strategy:
  //   - Mutating routes (POST/PUT/DELETE/PATCH) without auth: ERROR (blocks merge)
  //   - GET routes without auth: WARN (should be fixed but doesn't block)
  //
  // Known exceptions (legitimate public routes):
  //   - /api/auth/register — must be public for new users to sign up
  //   - /api/auth/forgot-password — must be public for password reset
  //   - /api/auth/[...nextauth] — NextAuth handler (has its own auth)
  //   - /api/health — public health check endpoint
  //   - /api/webhooks/* — use signature verification instead of session auth
  //
  // To disable for a specific file, add:
  //   /* eslint-disable zenic-security/api-auth-required */
  // Or for a single line:
  //   // eslint-disable-next-line zenic-security/api-auth-required
  plugins: {
    "zenic-security": {
      rules: {
        "api-auth-required": apiAuthRequired,
      },
    },
  },
  rules: {
    // ─── Phase 6.1: Auth enforcement strategy ───────────────────────
    // Escalation plan:
    //   Current: "warn" — 87 existing routes lack auth, not yet blocking
    //   Step 1:  "error" — after Phase 0.2 migration of remaining routes
    //   Step 2:  enforceGetRoutes: true — after GET routes are also secured
    //
    // The rule detects unauthenticated mutating endpoints (POST/PUT/DELETE/PATCH).
    // Warnings are tracked in the weekly health report as tech debt.
    // New routes MUST include auth from the start — use eslint-disable only
    // for legitimate public endpoints with a documented reason.
    "zenic-security/api-auth-required": ["warn", {
      enforceGetRoutes: false, // GET routes tracked but not enforced yet
    }],
  },
}, {
  // ─── Known public routes: downgrade auth rule to "warn" ───────────
  // These routes MUST be accessible without authentication.
  files: [
    "src/app/api/auth/register/**/*.ts",
    "src/app/api/auth/forgot-password/**/*.ts",
    "src/app/api/auth/[...nextauth]/**/*.ts",
    "src/app/api/health/**/*.ts",
    "src/app/api/webhooks/**/*.ts",
  ],
  rules: {
    "zenic-security/api-auth-required": "off",
  },
}, {
  ignores: [
    "node_modules/**",
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "rust-engine/**",
    "skills/**",
    "prisma/**",
    "eslint-rules/**",
  ],
}];

export default eslintConfig;
