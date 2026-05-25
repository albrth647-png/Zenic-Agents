// ─── Zenic-Agents v3 — Current User Profile API
// GET /api/user/profile — Returns authenticated user's profile with createdAt

import { NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { db } from "@/lib/db";

export async function GET() {
  try {
    const authUser = await getAuthUser();
    if (!authUser) {
      return NextResponse.json(
        { error: "No autenticado", code: "UNAUTHORIZED" },
        { status: 401 }
      );
    }

    const user = await db.user.findUnique({
      where: { id: authUser.userId },
      select: {
        id: true,
        email: true,
        name: true,
        avatar: true,
        role: true,
        status: true,
        isActive: true,
        lastLogin: true,
        createdAt: true,
        updatedAt: true,
        roles: {
          include: {
            role: {
              select: { name: true, description: true },
            },
          },
        },
      },
    });

    if (!user) {
      return NextResponse.json(
        { error: "Usuario no encontrado", code: "NOT_FOUND" },
        { status: 404 }
      );
    }

    // Derive subscription tier from user role
    // In production this would come from a Subscription table
    let subscriptionTier = "starter";
    if (user.role === "admin") subscriptionTier = "enterprise";
    else if (user.role === "operator") subscriptionTier = "business";

    return NextResponse.json({
      id: user.id,
      email: user.email,
      name: user.name,
      avatar: user.avatar,
      role: user.role,
      status: user.status,
      isActive: user.isActive,
      lastLogin: user.lastLogin?.toISOString() ?? null,
      createdAt: user.createdAt.toISOString(),
      updatedAt: user.updatedAt.toISOString(),
      subscriptionTier,
      rbacRoles: user.roles.map((ur) => ({
        name: ur.role.name,
        description: ur.role.description,
      })),
      activeSessions: 1, // Simplified — real impl would count Session table
    });
  } catch (error) {
    console.error("[/api/user/profile GET]", error);
    return NextResponse.json(
      { error: "Error al obtener perfil", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
