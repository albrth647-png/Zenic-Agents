import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // NOTA: NO usar output: "export" — elimina todas las API routes (login/signup fallan con 404)
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    unoptimized: true, // Necesario para Capacitor WebView
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
