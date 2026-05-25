import { User } from "lucide-react";

export default function ProfileLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <User className="h-10 w-10 text-emerald-400 mx-auto animate-pulse" />
        <p className="text-muted-foreground text-sm">Cargando perfil...</p>
      </div>
    </div>
  );
}
