import { Settings } from "lucide-react";

export default function SettingsLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center space-y-3">
        <Settings className="h-10 w-10 text-gray-400 mx-auto animate-spin" />
        <p className="text-muted-foreground text-sm">Cargando configuración...</p>
      </div>
    </div>
  );
}
