/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    base: env.VITE_BASE_PATH || "/",
    build: { chunkSizeWarningLimit: 1200 },
    // MapLibre charge son worker relativement à son propre fichier : ne pas le pré-empaqueter en dev.
    optimizeDeps: { exclude: ["maplibre-gl"] },
    // La collecte écrit dans public/data pendant que le serveur tourne : ne pas recharger la page à chaque fichier.
    server: { watch: { ignored: ["**/public/data/**", "**/.cache/**", "**/.venv/**"] } },
    test: { environment: "node", include: ["src/**/*.test.ts"] },
  };
});
