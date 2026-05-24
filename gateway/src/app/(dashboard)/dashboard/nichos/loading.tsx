import { FolderOpen } from "lucide-react";

export default function NichosLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <FolderOpen className="h-10 w-10 text-teal-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando nichos y plantillas...</p>
      </div>
    </div>
  );
}
