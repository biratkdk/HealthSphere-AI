import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // On Vercel the frontend and backend share the same origin, so no base URL
  // is needed — the axios client uses relative paths automatically.
  // For local dev, proxy /api to the backend process.
  const apiTarget = env.VITE_API_BASE_URL || "http://localhost:8000";
  const isVercel = Boolean(env.VERCEL);

  return {
    plugins: [react()],

    esbuild: {
      loader: "jsx",
      include: /src\/.*\.js$/,
      exclude: [],
    },

    optimizeDeps: {
      esbuildOptions: {
        loader: { ".js": "jsx" },
      },
    },

    server: {
      host: "0.0.0.0",
      port: 3000,
      // Dev proxy: avoids CORS issues when running backend separately.
      // On Vercel the same origin serves both, so no proxy is needed there.
      proxy: isVercel
        ? {}
        : {
            "/api": {
              target: apiTarget,
              changeOrigin: true,
              secure: false,
            },
          },
    },

    preview: {
      host: "0.0.0.0",
      port: 4173,
    },

    build: {
      // Fail the build if any chunk exceeds 1 MB (forces code-splitting review)
      chunkSizeWarningLimit: 1024,
      rollupOptions: {
        output: {
          // Separate vendor bundles for better long-term caching
          manualChunks: {
            react: ["react", "react-dom"],
            router: ["react-router-dom"],
            swr: ["swr"],
            axios: ["axios"],
          },
        },
      },
    },
  };
});
