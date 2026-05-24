"use client";

import { usePathname } from "next/navigation";
import { RefreshCw, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useSubscriptionContext } from "@/hooks/useUserProfile";
import { useRealtimeStatus } from "@/components/dashboard/RealtimeProvider";
import type { ConnectionStatus } from "@/hooks/useRealtimeEvents";

const routeLabels: Record<string, string> = {
  "/dashboard": "Centro de Comando",
  "/dashboard/arbitraje": "Estación de Arbitraje",
  "/dashboard/boveda": "Bóveda de Seguridad",
  "/dashboard/nichos": "Nichos y Plantillas",
  "/dashboard/apis": "APIs & MCP",
  "/dashboard/policies": "Políticas",
  "/dashboard/integrations": "Integraciones",
  "/dashboard/settings": "Configuración",
  "/dashboard/profile": "Perfil",
};

function getStatusConfig(status: ConnectionStatus) {
  switch (status) {
    case "connected":
      return {
        label: "En vivo",
        dotClass: "bg-emerald-500 animate-pulse",
        containerClass: "bg-emerald-50 dark:bg-emerald-950/20",
        textClass: "text-emerald-700 dark:text-emerald-400",
      };
    case "connecting":
      return {
        label: "Conectando...",
        dotClass: "bg-amber-500 animate-pulse",
        containerClass: "bg-amber-50 dark:bg-amber-950/20",
        textClass: "text-amber-700 dark:text-amber-400",
      };
    case "disconnected":
      return {
        label: "Sin conexión",
        dotClass: "bg-red-500",
        containerClass: "bg-red-50 dark:bg-red-950/20",
        textClass: "text-red-700 dark:text-red-400",
      };
  }
}

export default function DashboardHeader() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { ctx } = useSubscriptionContext();
  const realtimeStatus = useRealtimeStatus();

  const pageTitle = routeLabels[pathname] || "Panel de Control";
  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");

  // Sprint 6: Real tier badge from subscription context
  const tierNombre = ctx.nombreMostrar;
  const tierColor =
    ctx.tier === "enterprise" || ctx.tier === "on_premise_enterprise"
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
      : ctx.tier === "business"
        ? "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400"
        : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300";

  // Sprint 7: SSE connection status indicator
  const statusConfig = getStatusConfig(realtimeStatus);

  return (
    <header data-testid="dashboard-header" className="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border px-4 sm:px-6 py-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <SidebarTrigger className="shrink-0" />
          <div className="min-w-0">
            <h2 className="text-lg sm:text-xl font-bold text-foreground truncate">
              {pageTitle} — Zenic v3.0
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              La IA nunca genera — solo arbitra SÍ/NO
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <Badge data-testid="tier-badge" className={`${tierColor} text-[9px] px-2 py-1 border-0 font-semibold`}>
            {tierNombre}
          </Badge>
          <div data-testid="sse-status" role="status" aria-live="polite" className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${statusConfig.containerClass}`}>
            <span className={`w-2 h-2 rounded-full ${statusConfig.dotClass}`} />
            <span className={`text-[9px] font-semibold ${statusConfig.textClass}`}>
              {statusConfig.label}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={toggleTheme}
            title="Cambiar tema"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs">
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Actualizar
          </Button>
        </div>
      </div>
    </header>
  );
}
