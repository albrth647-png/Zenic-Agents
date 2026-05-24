/**
 * ─── Zenic-Agents v3 — Custom ESLint Rule: api-auth-required ─────────
 * Phase 6.1: Ensures all API route handlers (POST, PUT, DELETE, PATCH)
 * call an auth function (requireAuth, requireAuthAndPermission, getAuthUser,
 * requireTenantAuth) before processing the request.
 *
 * This prevents the reintroduction of unauthenticated API routes
 * that were identified as a critical vulnerability in Phase 0.
 *
 * Rationale:
 *   - POST/PUT/DELETE/PATCH are mutating operations that MUST have auth.
 *   - GET routes should at minimum call getAuthUser or requireAuth.
 *   - The rule scans function bodies for known auth function calls.
 */

/** @type {import('eslint').RuleModule} */
const apiAuthRequiredRule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Require authentication calls in API route handlers (POST, PUT, DELETE, PATCH)",
      category: "Security",
      recommended: true,
    },
    messages: {
      missingAuth:
        "API route handler '{{methodName}}' in '{{filePath}}' does not call any " +
        "authentication function (requireAuth, requireAuthAndPermission, getAuthUser, " +
        "requireTenantAuth). All mutating endpoints must authenticate the request.",
      missingAuthGet:
        "GET API route handler in '{{filePath}}' does not call any " +
        "authentication function. Consider adding at least getAuthUser() " +
        "to protect this endpoint.",
    },
    schema: [
      {
        type: "object",
        properties: {
          authFunctionPatterns: {
            type: "array",
            items: { type: "string" },
          },
          enforceGetRoutes: {
            type: "boolean",
            default: true,
          },
        },
        additionalProperties: false,
      },
    ],
  },

  create(context) {
    const options = context.options[0] || {};
    const authFunctionPatterns = options.authFunctionPatterns || [
      "requireAuth",
      "requireAuthAndPermission",
      "getAuthUser",
      "requireTenantAuth",
    ];
    const enforceGetRoutes = options.enforceGetRoutes !== false;

    const filename = context.getFilename();

    // Only apply to API route files
    if (
      !filename.includes("/api/") ||
      !filename.endsWith("route.ts") ||
      filename.includes("__tests__") ||
      filename.includes(".test.") ||
      filename.includes(".spec.")
    ) {
      return {};
    }

    /**
     * Check if a function body contains an auth call.
     * Walks the AST looking for CallExpression nodes that match
     * any of the known auth function patterns.
     */
    function hasAuthCall(node) {
      let found = false;

      function walk(n) {
        if (!n || typeof n !== "object") return;
        if (found) return;

        // Check CallExpression nodes
        if (
          n.type === "CallExpression" &&
          n.callee
        ) {
          const calleeName = getCalleeName(n.callee);
          if (calleeName && authFunctionPatterns.some((p) => calleeName.includes(p))) {
            found = true;
            return;
          }

          // Check destructured result: const { user } = await requireAuth(...)
          if (
            n.type === "CallExpression" &&
            n.parent &&
            n.parent.type === "AwaitExpression" &&
            n.parent.parent
          ) {
            // Already handled by callee check above
          }
        }

        // Check variable declarations for destructured auth calls
        // e.g., const { user } = await requireAuth(request)
        if (
          n.type === "VariableDeclarator" &&
          n.init &&
          n.init.type === "AwaitExpression" &&
          n.init.argument &&
          n.init.argument.type === "CallExpression"
        ) {
          const calleeName = getCalleeName(n.init.argument.callee);
          if (calleeName && authFunctionPatterns.some((p) => calleeName.includes(p))) {
            found = true;
            return;
          }
        }

        // Recurse into child nodes (but skip nested function scopes that
        // are NOT the handler — callbacks, closures, etc.)
        for (const key of Object.keys(n)) {
          if (key === "parent" || key === "loc" || key === "range" || key === "type") continue;
          const val = n[key];
          if (Array.isArray(val)) {
            for (const item of val) {
              if (item && typeof item === "object" && item.type) walk(item);
            }
          } else if (val && typeof val === "object" && val.type) {
            walk(val);
          }
        }
      }

      walk(node);
      return found;
    }

    /**
     * Extract the function name from a callee expression.
     * Handles: identifier, member expression, and destructured patterns.
     */
    function getCalleeName(callee) {
      if (!callee) return null;
      if (callee.type === "Identifier") return callee.name;
      if (callee.type === "MemberExpression") {
        // e.g., lib.auth.requireAuth → "requireAuth"
        if (callee.property && callee.property.type === "Identifier") {
          return callee.property.name;
        }
      }
      return null;
    }

    /**
     * Get the HTTP method name from an exported function name.
     */
    function getHttpMethod(name) {
      const methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"];
      return methods.find((m) => name.toUpperCase() === m) || null;
    }

    return {
      // Match exported async function declarations:
      //   export async function POST(request: NextRequest) { ... }
      "ExportNamedDeclaration > FunctionDeclaration"(node) {
        const methodName = node.id ? node.id.name : null;
        if (!methodName) return;

        const httpMethod = getHttpMethod(methodName);
        if (!httpMethod) return;

        const isMutating = ["POST", "PUT", "DELETE", "PATCH"].includes(httpMethod);

        if (isMutating && !hasAuthCall(node.body)) {
          context.report({
            node,
            messageId: "missingAuth",
            data: {
              methodName: httpMethod,
              filePath: filename,
            },
          });
        } else if (!isMutating && enforceGetRoutes && !hasAuthCall(node.body)) {
          context.report({
            node,
            messageId: "missingAuthGet",
            data: {
              filePath: filename,
            },
          });
        }
      },

      // Match exported arrow function variable declarations:
      //   export const POST = async (request: NextRequest) => { ... }
      "ExportNamedDeclaration > VariableDeclaration"(node) {
        for (const declarator of node.declarations) {
          if (
            !declarator.id ||
            declarator.id.type !== "Identifier" ||
            !declarator.init
          ) {
            continue;
          }

          const methodName = declarator.id.name;
          const httpMethod = getHttpMethod(methodName);
          if (!httpMethod) continue;

          const isMutating = ["POST", "PUT", "DELETE", "PATCH"].includes(httpMethod);

          // Get the function body
          let body = null;
          if (
            declarator.init.type === "ArrowFunctionExpression" ||
            declarator.init.type === "FunctionExpression"
          ) {
            body = declarator.init.body;
          } else if (
            declarator.init.type === "CallExpression" &&
            declarator.init.arguments.length > 0
          ) {
            // Handle wrapped handlers like: export const POST = withAuth(async () => { ... })
            // The body is in the last argument
            const lastArg =
              declarator.init.arguments[declarator.init.arguments.length - 1];
            if (
              lastArg &&
              (lastArg.type === "ArrowFunctionExpression" ||
                lastArg.type === "FunctionExpression")
            ) {
              body = lastArg.body;
            }
          }

          if (!body) continue;

          if (isMutating && !hasAuthCall(body)) {
            context.report({
              node: declarator,
              messageId: "missingAuth",
              data: {
                methodName: httpMethod,
                filePath: filename,
              },
            });
          } else if (!isMutating && enforceGetRoutes && !hasAuthCall(body)) {
            context.report({
              node: declarator,
              messageId: "missingAuthGet",
              data: {
                filePath: filename,
              },
            });
          }
        }
      },
    };
  },
};

module.exports = apiAuthRequiredRule;
