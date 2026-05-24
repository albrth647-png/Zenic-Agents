"use client";

import { useState, useEffect, useCallback } from "react";
import { Shield, Search, Plus, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EstadoVacio, EstadoError, EstadoCargando } from "@/components/ui/data-states";
import { apiFetch, type ApiError } from "@/lib/api-client";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Policies Page — Real API data from /api/v1/policies
// No more hardcoded policy objects. Fetches from the declarative policy engine.
// ═══════════════════════════════════════════════════════════════════════════════

interface PolicyListItem {
  policyId: string;
  name: string;
  description: string;
  version: string;
  labels: Record<string, string>;
  compliance: string[];
  statementCount: number;
  testCount: number;
  isActive: boolean;
  contentHash: string;
  author: string | null;
  createdAt: string;
  updatedAt: string;
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicyListItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState<string>("all");
  const [total, setTotal] = useState(0);

  const cargarPoliticas = useCallback(async () => {
    setCargando(true);
    try {
      const params = new URLSearchParams({ pageSize: "50" });
      if (filtroEstado !== "all") params.set("isActive", filtroEstado);
      const data = await apiFetch<{
        success: boolean;
        data: PolicyListItem[];
        total: number;
      }>(`/api/v1/policies?${params.toString()}`);
      setPolicies(data.data || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err: any) {
      setError(err);
    } finally {
      setCargando(false);
    }
  }, [filtroEstado]);

  useEffect(() => {
    cargarPoliticas();
  }, [cargarPoliticas]);

  const politicasFiltradas = policies.filter((p) => {
    if (!busqueda) return true;
    const q = busqueda.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q) ||
      p.policyId.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Políticas</h1>
          <p className="text-sm text-muted-foreground">
            Gestiona las políticas de seguridad y compliance — {total} política{total !== 1 ? "s" : ""} registrada{total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Política
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar políticas por nombre, descripción o ID..."
            className="pl-9"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>
        <Select value={filtroEstado} onValueChange={setFiltroEstado}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
            <SelectValue placeholder="Filtrar estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            <SelectItem value="true">Activas</SelectItem>
            <SelectItem value="false">Inactivas</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {cargando ? (
        <EstadoCargando mensaje="Cargando políticas..." />
      ) : error ? (
        <EstadoError
          error={error}
          titulo="Error al cargar políticas"
          onReintentar={cargarPoliticas}
        />
      ) : politicasFiltradas.length === 0 ? (
        <EstadoVacio
          icon={Shield}
          titulo={busqueda ? "Sin resultados" : "No hay políticas registradas"}
          descripcion={
            busqueda
              ? `No se encontraron políticas que coincidan con "${busqueda}"`
              : "Las políticas declarativas se crean desde el motor de políticas o se cargan desde archivos YAML"
          }
          accion={
            !busqueda
              ? { etiqueta: "Cargar desde YAML", onClick: () => {} }
              : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {politicasFiltradas.map((policy) => (
            <Card
              key={policy.policyId}
              className="border-0 shadow-sm hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold text-foreground truncate">
                    {policy.name}
                  </CardTitle>
                  <Badge
                    className={`text-[8px] px-1.5 py-0 border-0 font-bold shrink-0 ${
                      policy.isActive
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400"
                    }`}
                  >
                    {policy.isActive ? "ACTIVA" : "INACTIVA"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-[11px] text-muted-foreground line-clamp-2 mb-3">
                  {policy.description || "Sin descripción"}
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    className={`text-[9px] px-2 py-0.5 border-0 ${
                      policy.statementCount > 0
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400"
                        : "bg-gray-100 text-gray-500 dark:bg-gray-500/20 dark:text-gray-400"
                    }`}
                  >
                    {policy.statementCount} regla{policy.statementCount !== 1 ? "s" : ""}
                  </Badge>
                  <Badge
                    className={`text-[9px] px-2 py-0.5 border-0 ${
                      policy.testCount > 0
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
                        : "bg-gray-100 text-gray-500 dark:bg-gray-500/20 dark:text-gray-400"
                    }`}
                  >
                    {policy.testCount} test{policy.testCount !== 1 ? "s" : ""}
                  </Badge>
                  <span className="text-[9px] text-muted-foreground/60 font-mono">
                    v{policy.version}
                  </span>
                </div>
                {policy.author && (
                  <p className="text-[10px] text-muted-foreground/50 mt-2">
                    Por {policy.author}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
