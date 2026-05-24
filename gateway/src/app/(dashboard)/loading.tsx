import { Cpu } from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════════
// Sprint 6: Dashboard Loading State
// Shown while dashboard sub-routes are loading their data.
// ═══════════════════════════════════════════════════════════════════════════════

export default function DashboardLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-4">
        <Cpu className="h-10 w-10 text-emerald-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm tracking-widest uppercase">
          Cargando...
        </p>
      </div>
    </div>
  );
}
