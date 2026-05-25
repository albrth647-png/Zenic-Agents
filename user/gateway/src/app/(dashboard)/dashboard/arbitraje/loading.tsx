import { Gavel } from "lucide-react";

export default function ArbitrajeLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <Gavel className="h-10 w-10 text-amber-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando estación de arbitraje...</p>
      </div>
    </div>
  );
}
