"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Gavel,
  Vault,
  FolderOpen,
  Key,
  Shield,
  Activity,
  Settings,
  User,
  LogOut,
  ChevronDown,
  Lock,
  Crown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { useAuth } from "@/components/auth/useAuth";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: string;
  subtexto?: string;
  children?: {
    label: string;
    href: string;
    bloqueado?: boolean;
    tierRequerido?: string;
    badge?: string;
    badgeColor?: string;
  }[];
}

const navItems: NavItem[] = [
  {
    label: "CENTRO DE COMANDO",
    href: "/dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
    subtexto: "Activo",
  },
  {
    label: "ARBITRAJE",
    href: "/dashboard/arbitraje",
    icon: <Gavel className="h-4 w-4" />,
    subtexto: "Sin pendientes",
  },
  {
    label: "BÓVEDA DE SEGURIDAD",
    href: "/dashboard/boveda",
    icon: <Vault className="h-4 w-4" />,
  },
  {
    label: "NICHOS Y PLANTILLAS",
    href: "/dashboard/nichos",
    icon: <FolderOpen className="h-4 w-4" />,
    subtexto: "Conexiones",
  },
  {
    label: "APIS & MCP",
    href: "/dashboard/apis",
    icon: <Key className="h-4 w-4" />,
    subtexto: "Conexiones",
  },
  {
    label: "POLÍTICAS",
    href: "/dashboard/policies",
    icon: <Shield className="h-4 w-4" />,
    children: [
      { label: "Reglas de Seguridad", href: "/dashboard/policies" },
      {
        label: "Registro de Auditoría",
        href: "/dashboard/policies",
        bloqueado: true,
        tierRequerido: "Business",
      },
    ],
  },
  {
    label: "INTEGRACIONES",
    href: "/dashboard/integrations",
    icon: <Activity className="h-4 w-4" />,
  },
  {
    label: "CONFIGURACIÓN",
    href: "/dashboard/settings",
    icon: <Settings className="h-4 w-4" />,
  },
  {
    label: "PERFIL",
    href: "/dashboard/profile",
    icon: <User className="h-4 w-4" />,
  },
];

export default function DashboardSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { openMobile, setOpenMobile } = useSidebar();
  const [expanded, setExpanded] = useState<string[]>(["POLÍTICAS"]);

  const isActive = (href: string) => pathname === href;
  const toggleExpand = (label: string) =>
    setExpanded((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]
    );

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "ZN";

  const roleLabel =
    user?.role === "admin"
      ? "Administrador"
      : user?.role === "operator"
        ? "Operador"
        : "Usuario";

  return (
    <Sidebar
      side="left"
      variant="sidebar"
      collapsible="offcanvas"
      className="border-r-0"
    >
      {/* Custom dark background overlay */}
      <div className="flex h-full flex-col bg-[#1A1D2E] text-white">
        {/* ─── Header / Logo ─── */}
        <SidebarHeader className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold tracking-wider">ZENIC</h1>
              <p className="text-[11px] text-white/40 tracking-widest uppercase">
                Plataforma Empresarial
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-[10px] text-emerald-400" role="status">En línea</span>
            </div>
          </div>
        </SidebarHeader>

        {/* ─── Navigation ─── */}
        <SidebarContent className="px-3 py-4" data-testid="sidebar-nav">
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu role="navigation" aria-label="Navegación principal">
                {navItems.map((item) => {
                  const active = isActive(item.href);

                  if (item.children) {
                    return (
                      <SidebarMenuItem key={item.label}>
                        <SidebarMenuButton
                          isActive={active}
                          className={cn(
                            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                            active
                              ? "bg-white/10 text-white hover:bg-white/10 hover:text-white"
                              : "text-white/60 hover:bg-white/5 hover:text-white/90"
                          )}
                          onClick={() => toggleExpand(item.label)}
                          tooltip={item.label}
                          aria-expanded={expanded.includes(item.label)}
                          data-testid={`nav-item-${item.label}`}
                        >
                          <span className="shrink-0">{item.icon}</span>
                          <div className="flex-1 min-w-0">
                            <span className="text-[11px] font-semibold tracking-wider block truncate">
                              {item.label}
                            </span>
                            {item.subtexto && (
                              <span className="text-[10px] text-white/35 block truncate">
                                {item.subtexto}
                              </span>
                            )}
                          </div>
                          <ChevronDown
                            className={cn(
                              "h-3.5 w-3.5 shrink-0 transition-transform",
                              expanded.includes(item.label) ? "rotate-180" : ""
                            )}
                          />
                        </SidebarMenuButton>
                        {expanded.includes(item.label) && (
                          <SidebarMenuSub className="ml-0 border-white/10">
                            {item.children.map((child) => (
                              <SidebarMenuSubItem key={child.label}>
                                <SidebarMenuSubButton
                                  asChild
                                  isActive={isActive(child.href) && !child.bloqueado}
                                  className={cn(
                                    "flex items-center justify-between px-3 py-1.5 text-[11px] rounded transition-colors",
                                    child.bloqueado
                                      ? "text-white/20 cursor-not-allowed pointer-events-none"
                                      : "text-white/45 hover:text-white/90"
                                  )}
                                >
                                  <Link
                                    href={child.bloqueado ? "#" : child.href}
                                    onClick={(e) => {
                                      if (child.bloqueado) e.preventDefault();
                                      // Close mobile sidebar on nav
                                      if (openMobile) setOpenMobile(false);
                                    }}
                                    className="flex items-center justify-between w-full"
                                  >
                                    <span className="flex items-center gap-1.5 truncate">
                                      {child.bloqueado && (
                                        <Lock className="h-3 w-3 text-white/20 shrink-0" />
                                      )}
                                      <span className="truncate">{child.label}</span>
                                    </span>
                                    {child.bloqueado && (
                                      <Badge className="bg-white/10 text-white/30 text-[7px] px-1 py-0 border-0 font-bold shrink-0">
                                        <Crown className="h-2.5 w-2.5 mr-0.5" />
                                        {child.tierRequerido}
                                      </Badge>
                                    )}
                                  </Link>
                                </SidebarMenuSubButton>
                              </SidebarMenuSubItem>
                            ))}
                          </SidebarMenuSub>
                        )}
                      </SidebarMenuItem>
                    );
                  }

                  return (
                    <SidebarMenuItem key={item.label}>
                      <SidebarMenuButton
                        asChild
                        isActive={active}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                          active
                            ? "bg-white/10 text-white hover:bg-white/10 hover:text-white"
                            : "text-white/60 hover:bg-white/5 hover:text-white/90"
                        )}
                        tooltip={item.label}
                        aria-current={active ? "page" : undefined}
                        data-testid={`nav-item-${item.label}`}
                      >
                        <Link
                          href={item.href}
                          onClick={() => {
                            // Close mobile sidebar on nav
                            if (openMobile) setOpenMobile(false);
                          }}
                          className="flex items-center gap-3 w-full"
                        >
                          <span className="shrink-0">{item.icon}</span>
                          <div className="flex-1 min-w-0">
                            <span className="text-[11px] font-semibold tracking-wider block truncate">
                              {item.label}
                            </span>
                            {item.subtexto && (
                              <span className="text-[10px] text-white/35 block truncate">
                                {item.subtexto}
                              </span>
                            )}
                          </div>
                          {item.badge && (
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded-full text-white shrink-0 ${item.badgeColor || "bg-amber-500"}`}
                            >
                              {item.badge}
                            </span>
                          )}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <Separator className="bg-white/10" />

        {/* ─── User info footer ─── */}
        <SidebarFooter className="px-4 py-4">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-xs font-bold shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.name || "Cargando..."}
              </p>
              <p className="text-[10px] text-white/35 truncate">
                {roleLabel}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-white/30 hover:text-white/60 hover:bg-transparent"
              onClick={logout}
              title="Cerrar sesión"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </SidebarFooter>
      </div>

      <SidebarRail className="bg-white/5 hover:bg-white/10" />
    </Sidebar>
  );
}
