import { Key } from "lucide-react";

export default function ApisLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <Key className="h-10 w-10 text-emerald-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando APIs y MCP...</p>
      </div>
    </div>
  );
}
