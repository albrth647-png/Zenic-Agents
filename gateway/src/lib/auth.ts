import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';
import { NextRequest } from 'next/server';
import crypto from 'crypto';

export interface AuthUser {
  id: string;
  email: string;
  name?: string | null;
  role: string;
}

/**
 * Get the authenticated user from the session or API key.
 * Supports both NextAuth session and API key authentication.
 *
 * #41 Fix: All API endpoints MUST use this function to verify identity.
 */
export async function getAuthUser(req?: NextRequest): Promise<AuthUser | null> {
  // Method 1: NextAuth session
  const session = await getServerSession(authOptions);
  if (session?.user) {
    return {
      id: (session.user as any).id,
      email: session.user.email!,
      name: session.user.name,
      role: (session.user as any).role || 'user',
    };
  }

  // Method 2: API Key in Authorization header
  if (req) {
    const authHeader = req.headers.get('authorization');
    if (authHeader?.startsWith('Bearer ')) {
      const apiKey = authHeader.substring(7);
      const validApiKey = process.env.API_SECRET_KEY;
      if (validApiKey && apiKey === validApiKey) {
        // Look up the admin user from DB for valid foreign key references
        try {
          const { db } = await import('@/lib/db');
          const admin = await db.user.findFirst({ where: { role: 'admin', isActive: true } });
          if (admin) {
            return {
              id: admin.id,
              email: admin.email,
              name: admin.name,
              role: 'admin',
            };
          }
        } catch { /* fallback */ }
        return {
          id: 'api-key-user',
          email: 'system@api.local',
          name: 'API System User',
          role: 'admin',
        };
      }
    }

    // Method 3: HMAC-signed request verification (#42 fix)
    const signature = req.headers.get('x-request-signature');
    const timestamp = req.headers.get('x-request-timestamp');
    if (signature && timestamp) {
      const verified = verifyRequestSignature(req.url, timestamp, signature);
      if (verified) {
        return {
          id: 'signed-request-user',
          email: 'system@signed.local',
          name: 'Signed Request User',
          role: 'operator',
        };
      }
    }
  }

  return null;
}

/**
 * Verify that a user has the required minimum role.
 * Role hierarchy: user < operator < admin
 */
export function hasMinRole(userRole: string, requiredRole: string): boolean {
  const roleLevel: Record<string, number> = {
    user: 1,
    operator: 2,
    admin: 3,
  };
  return (roleLevel[userRole] || 0) >= (roleLevel[requiredRole] || 0);
}

/**
 * #42 Fix: Verify HMAC request signature to prevent feature gate spoofing.
 * Instead of trusting headers directly, we verify the signature
 * was generated server-side with our secret key.
 */
function verifyRequestSignature(url: string, timestamp: string, signature: string): boolean {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) return false;

  // Reject requests older than 5 minutes
  const ts = parseInt(timestamp, 10);
  if (isNaN(ts) || Math.abs(Date.now() - ts) > 5 * 60 * 1000) {
    return false;
  }

  // Verify HMAC
  const message = `${url}:${timestamp}`;
  const expected = crypto.createHmac('sha256', secret).update(message).digest('hex');

  // Timing-safe comparison to prevent timing attacks
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expected, 'hex')
    );
  } catch {
    return false;
  }
}

/**
 * Generate a signed request signature for server-to-server calls.
 * This should be used when the backend needs to call its own API.
 */
export function generateRequestSignature(url: string): { signature: string; timestamp: string } {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) throw new Error('NEXTAUTH_SECRET not configured');

  const timestamp = Date.now().toString();
  const message = `${url}:${timestamp}`;
  const signature = crypto.createHmac('sha256', secret).update(message).digest('hex');

  return { signature, timestamp };
}

// ─── Unified Auth Guards (Phase 0 — F0.6) ────────────────────────────────
// These wrappers enforce authentication consistently across all API routes.
// CRITICAL: Every POST/PUT/DELETE/PATCH endpoint MUST use one of these.

export interface AuthResult {
  user: AuthUser;
}

/**
 * Require authentication — any authenticated user is allowed.
 * Returns the authenticated user or throws a 401 response.
 *
 * Usage:
 *   const { user } = await requireAuth(request);
 */
export async function requireAuth(req: NextRequest): Promise<AuthResult> {
  const user = await getAuthUser(req);
  if (!user) {
    throw new AuthError('Authentication required', 401, 'UNAUTHORIZED');
  }
  return { user };
}

/**
 * Require authentication AND a minimum role.
 * Role hierarchy: user < operator < admin
 *
 * Usage:
 *   const { user } = await requireAuthAndPermission(request, 'operator');
 */
export async function requireAuthAndPermission(
  req: NextRequest,
  minRole: 'user' | 'operator' | 'admin' = 'operator',
): Promise<AuthResult> {
  const { user } = await requireAuth(req);
  if (!hasMinRole(user.role, minRole)) {
    throw new AuthError(
      `Insufficient permissions: requires '${minRole}' role, got '${user.role}'`,
      403,
      'FORBIDDEN',
    );
  }
  return { user };
}

/**
 * Custom error class for auth failures that can be caught in route handlers
 * and converted to proper NextResponse objects.
 */
export class AuthError extends Error {
  public readonly statusCode: number;
  public readonly code: string;

  constructor(message: string, statusCode: number, code: string) {
    super(message);
    this.name = 'AuthError';
    this.statusCode = statusCode;
    this.code = code;
  }

  /** Convert to a standard JSON NextResponse */
  toResponse(): Response {
    return Response.json(
      { success: false, error: this.message, code: this.code },
      { status: this.statusCode },
    );
  }
}

/**
 * Helper to handle AuthError in route catch blocks.
 * If the error is an AuthError, return its response; otherwise rethrow.
 *
 * Usage:
 *   try {
 *     const { user } = await requireAuth(request);
 *     // ... route logic
 *   } catch (error) {
 *     if (handleAuthError(error)) return handleAuthError(error);
 *     throw error;
 *   }
 */
export function handleAuthError(error: unknown): Response | null {
  if (error instanceof AuthError) {
    return error.toResponse();
  }
  return null;
}
