import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_BASE_URL || "http://localhost:8000";

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
      // Dev proxy: avoids CORS issues when running backend separately
      proxy: {
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
