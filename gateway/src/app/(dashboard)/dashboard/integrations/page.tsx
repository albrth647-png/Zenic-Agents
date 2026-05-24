"use client";

import { useState, useEffect, useCallback } from "react";
import { Activity, Plus, Cable, Server, RefreshCw, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EstadoVacio, EstadoError, EstadoCargando } from "@/components/ui/data-states";
import { apiFetch, type ApiError } from "@/lib/api-client";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Integrations Page — Real data from /api/mcp/servers
// Shows actual MCP server connections instead of hardcoded Slack/GitHub/Jira.
// ═══════════════════════════════════════════════════════════════════════════════

interface McpServerInfo {
  id: string;
  name: string;
  displayName: string | null;
  description: string | null;
  status: string;
  url: string | null;
  protocol: string;
  toolCount?: number;
  createdAt: string;
  updatedAt: string;
}

export default function IntegrationsPage() {
  const [servers, setServers] = useState<McpServerInfo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const cargarServidores = useCallback(async () => {
    setCargando(true);
    try {
      const data = await apiFetch<{ success: boolean; data: McpServerInfo[] }>(
        "/api/mcp/servers"
      );
      setServers(data.data || []);
      setError(null);
    } catch (err: any) {
      setError(err);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargarServidores();
  }, [cargarServidores]);

  const conectados = servers.filter((s) => s.status === "active").length;
  const disponibles = servers.filter((s) => s.status !== "active").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Integraciones</h1>
          <p className="text-sm text-muted-foreground">
            Servidores MCP conectados — {conectados} activo{conectados !== 1 ? "s" : ""}, {disponibles} disponible{disponibles !== 1 ? "s" : ""}
          </p>
        </div>
        <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
          <Plus className="h-4 w-4 mr-2" />
          Añadir Integración
        </Button>
      </div>

      {cargando ? (
        <EstadoCargando mensaje="Cargando integraciones..." />
      ) : error ? (
        <EstadoError
          error={error}
          titulo="Error al cargar integraciones"
          onReintentar={cargarServidores}
        />
      ) : servers.length === 0 ? (
        <EstadoVacio
          icon={Activity}
          titulo="No hay integraciones configuradas"
          descripcion="Conecta herramientas y servicios a través del Gateway MCP para habilitar capacidades de automatización"
          accion={{ etiqueta: "Explorar integraciones", onClick: () => {} }}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {servers.map((server) => {
              const isActive = server.status === "active";
              return (
                <Card
                  key={server.id}
                  className="border-0 shadow-sm hover:shadow-md transition-shadow"
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            isActive
                              ? "bg-emerald-50 dark:bg-emerald-500/10"
                              : "bg-muted"
                          }`}
                        >
                          <Server
                            className={`h-5 w-5 ${
                              isActive
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-muted-foreground"
                            }`}
                          />
                        </div>
                        <div className="min-w-0">
                          <CardTitle className="text-sm font-semibold text-foreground truncate">
                            {server.displayName || server.name}
                          </CardTitle>
                          <p className="text-[10px] text-muted-foreground truncate">
                            {server.protocol}
                          </p>
                        </div>
                      </div>
                      <Badge
                        className={`text-[8px] px-1.5 py-0 border-0 font-bold shrink-0 ${
                          isActive
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400"
                            : server.status === "error"
                              ? "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"
                              : "bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-white/60"
                        }`}
                      >
                        {isActive ? "CONECTADO" : server.status === "error" ? "ERROR" : "DISPONIBLE"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-[11px] text-muted-foreground mb-3 line-clamp-2">
                      {server.description || `Servidor MCP ${server.protocol} para integración de herramientas`}
                    </p>
                    <div className="flex items-center justify-between">
                      {server.toolCount !== undefined && (
                        <span className="text-[10px] text-muted-foreground">
                          {server.toolCount} herramienta{server.toolCount !== 1 ? "s" : ""}
                        </span>
                      )}
                      <Button
                        variant={isActive ? "outline" : "default"}
                        size="sm"
                        className={
                          isActive
                            ? ""
                            : "bg-emerald-600 hover:bg-emerald-700 text-white"
                        }
                      >
                        {isActive ? "Configurar" : "Conectar"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="border-0 shadow-sm border-dashed border-2 border-border">
            <CardContent className="py-8 text-center">
              <Cable className="h-10 w-10 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground font-medium">
                Conecta herramientas personalizadas
              </p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Añade servidores MCP adicionales a través del Gateway para ampliar las capacidades de la plataforma
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
