"use client";

import { useSession, signOut } from "next-auth/react";
import { useCallback } from "react";

export function useAuth() {
  const { data: session, status } = useSession();

  const isAuthenticated = status === "authenticated";
  const isLoading = status === "loading";

  const user = session?.user
    ? {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        id: (session.user as any).id ?? "",
        name: session.user.name ?? "",
        email: session.user.email ?? "",
        avatar: session.user.image ?? "",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        role: (session.user as any).role ?? "user",
      }
    : null;

  const logout = useCallback(() => {
    signOut({ callbackUrl: "/auth/login" });
  }, []);

  return { user, isAuthenticated, isLoading, role: user?.role ?? null, logout };
}
