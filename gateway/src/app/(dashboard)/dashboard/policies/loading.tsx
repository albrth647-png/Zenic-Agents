import { Shield } from "lucide-react";

export default function PoliciesLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <Shield className="h-10 w-10 text-blue-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando políticas...</p>
      </div>
    </div>
  );
}
