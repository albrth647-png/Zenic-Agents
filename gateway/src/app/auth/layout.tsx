import { Shield } from "lucide-react";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex bg-background">
      {/* Panel izquierdo — Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-sidebar flex-col justify-between p-12 text-sidebar-foreground relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="h-8 w-8 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-wider">ZENIC</h1>
          </div>
          <p className="text-sidebar-foreground/50 text-sm tracking-widest uppercase">
            Plataforma Empresarial
          </p>
        </div>
        <div className="relative z-10 space-y-6">
          <h2 className="text-3xl font-bold leading-tight">
            IA enjaulada.
            <br />
            Seguridad por diseño.
            <br />
            Determinismo garantizado.
          </h2>
          <p className="text-sidebar-foreground/60 text-base max-w-md">
            La plataforma donde la IA nunca genera — solo arbitra SÍ/NO. Control
            total, transparencia absoluta, cumplimiento normativo.
          </p>
          <div className="flex items-center gap-6 pt-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">100%</p>
              <p className="text-xs text-sidebar-foreground/50 uppercase tracking-wider">
                Determinista
              </p>
            </div>
            <div className="w-px h-10 bg-sidebar-foreground/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">0</p>
              <p className="text-xs text-sidebar-foreground/50 uppercase tracking-wider">
                Alucinaciones
              </p>
            </div>
            <div className="w-px h-10 bg-sidebar-foreground/10" />
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">BLAKE3</p>
              <p className="text-xs text-sidebar-foreground/50 uppercase tracking-wider">
                Integridad
              </p>
            </div>
          </div>
        </div>
        <div className="relative z-10 text-xs text-sidebar-foreground/30">
          &copy; {new Date().getFullYear()} Zenic Logic — Todos los derechos
          reservados
        </div>
        {/* Fondo decorativo */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-1/4 right-1/4 w-64 h-64 rounded-full bg-emerald-400 blur-3xl" />
          <div className="absolute bottom-1/4 left-1/4 w-48 h-48 rounded-full bg-teal-400 blur-3xl" />
        </div>
      </div>

      {/* Panel derecho — Formulario */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
