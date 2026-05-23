"use client";

import { useCallback, useState } from "react";
import { User, Mail, Shield, Calendar, Save } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EstadoCargando, EstadoError } from "@/components/ui/data-states";
import { useUserProfile } from "@/hooks/useUserProfile";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Profile Page — Real data from /api/user/profile
// Shows actual createdAt date, real email from session, real role.
// ═══════════════════════════════════════════════════════════════════════════════

export default function ProfilePage() {
  const { profile, cargando, error, recargar } = useUserProfile();
  const [guardando, setGuardando] = useState(false);

  const userName = profile?.name || "Usuario";
  const userEmail = profile?.email || "";
  const userRole = profile?.role || "user";
  const userInitials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const formatDate = (isoDate: string | null | undefined) => {
    if (!isoDate) return "Desconocida";
    try {
      return new Date(isoDate).toLocaleDateString("es", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    } catch {
      return "Desconocida";
    }
  };

  const tierLabel =
    profile?.subscriptionTier === "enterprise"
      ? "ENTERPRISE"
      : profile?.subscriptionTier === "business"
        ? "BUSINESS"
        : "STARTER";

  const manejarGuardar = useCallback(async () => {
    setGuardando(true);
    // In full implementation: PUT /api/user/profile with updated name
    await new Promise((r) => setTimeout(r, 800));
    setGuardando(false);
  }, []);

  if (cargando) {
    return <EstadoCargando mensaje="Cargando perfil..." />;
  }

  if (error) {
    return (
      <EstadoError
        error={error}
        titulo="Error al cargar perfil"
        onReintentar={recargar}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Profile Header */}
      <Card className="border-0 shadow-sm">
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="bg-gradient-to-br from-emerald-400 to-teal-600 text-white text-lg font-bold">
                {userInitials}
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-lg font-bold text-foreground">{userName}</h2>
              <p className="text-sm text-muted-foreground">{userEmail}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 text-[9px] px-2 py-0 border-0 font-semibold">
                  {userRole === "admin" ? "ADMINISTRADOR" : userRole === "operator" ? "OPERADOR" : "USUARIO"}
                </Badge>
                <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400 text-[9px] px-2 py-0 border-0 font-semibold">
                  {tierLabel}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Profile Info */}
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
            <User className="h-4 w-4 text-emerald-500" />
            Información Personal
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">Nombre</Label>
              <Input defaultValue={userName} className="text-sm" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Correo Electrónico</Label>
              <Input defaultValue={userEmail} className="text-sm" disabled />
            </div>
          </div>
          <Separator />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Rol</p>
                <p className="text-sm font-medium text-foreground capitalize">
                  {userRole}
                </p>
                {profile?.rbacRoles && profile.rbacRoles.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {profile.rbacRoles.map((r) => (
                      <Badge
                        key={r.name}
                        className="text-[8px] px-1.5 py-0 border-0 bg-muted text-muted-foreground"
                      >
                        {r.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Miembro desde</p>
                <p className="text-sm font-medium text-foreground">
                  {formatDate(profile?.createdAt)}
                </p>
              </div>
            </div>
          </div>
          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white mt-2 gap-2"
            onClick={manejarGuardar}
            disabled={guardando}
          >
            <Save className="h-4 w-4" />
            {guardando ? "Guardando..." : "Guardar Cambios"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
