import { Activity } from "lucide-react";

export default function IntegrationsLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <Activity className="h-10 w-10 text-violet-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando integraciones...</p>
      </div>
    </div>
  );
}
