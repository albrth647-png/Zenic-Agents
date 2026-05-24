"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function NichosError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.error("[Nichos Error]", error);
    }
  }, [error]);

  return (
    <div className="flex items-center justify-center py-20 px-6">
      <div className="text-center space-y-5 max-w-md">
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center">
            <AlertTriangle className="h-7 w-7 text-red-400" />
          </div>
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-bold text-foreground">Error en Nichos y Plantillas</h2>
          <p className="text-sm text-muted-foreground">
            No se pudieron cargar los nichos y plantillas. Intenta de nuevo.
          </p>
          {process.env.NODE_ENV === "development" && (
            <p className="text-red-400/70 text-xs font-mono mt-2 break-all">{error.message}</p>
          )}
        </div>
        <Button onClick={reset} className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2">
          <RefreshCw className="h-4 w-4" />
          Reintentar
        </Button>
      </div>
    </div>
  );
}
