import { NextResponse } from "next/server";
import { z } from "zod";
import crypto from "crypto";
import { db } from "@/lib/db";
import { createRedactedLogger } from "@/lib/security/log-redact";

const logger = createRedactedLogger(console);

const forgotPasswordSchema = z.object({
  email: z.string().email("Correo electrónico inválido"),
});

/**
 * POST /api/auth/forgot-password
 *
 * Generates a password-reset token, stores it in the database with an
 * expiration, and returns a success response regardless of whether the
 * email exists (to prevent email-enumeration attacks).
 *
 * In production, an email service should be integrated to actually send
 * the reset link. For now, the token is stored and the reset page can
 * validate it directly.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const parsed = forgotPasswordSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: "Correo electrónico inválido", details: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const { email } = parsed.data;

    // Always return success to prevent email-enumeration attacks.
    // An attacker should not be able to determine if an email is registered.
    const successResponse = NextResponse.json(
      { message: "Si existe una cuenta con ese correo, recibirás un enlace para restablecer tu contraseña." },
      { status: 200 },
    );

    // Look up the user
    const user = await db.user.findUnique({ where: { email } });
    if (!user) {
      // User doesn't exist — return success anyway to prevent enumeration
      logger.info("[forgot-password] Reset requested for unregistered email");
      return successResponse;
    }

    // Invalidate any existing reset tokens for this user
    await db.passwordResetToken.deleteMany({
      where: { userId: user.id },
    });

    // Generate a cryptographically secure reset token
    const resetToken = crypto.randomBytes(32).toString("hex");
    const hashedToken = crypto.createHash("sha256").update(resetToken).digest("hex");

    // Token expires in 1 hour
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000);

    // Store the hashed token in the database
    await db.passwordResetToken.create({
      data: {
        userId: user.id,
        token: hashedToken,
        expiresAt,
      },
    });

    // In production, send email with reset link containing the token.
    // Example: sendResetEmail(user.email, resetToken);
    // For now, log that a token was generated (the token itself is never logged).
    logger.info(`[forgot-password] Reset token generated for user ${user.id}`);

    return successResponse;
  } catch (error) {
    logger.error("[forgot-password] Error:", error);
    return NextResponse.json(
      { error: "Error interno del servidor" },
      { status: 500 },
    );
  }
}
