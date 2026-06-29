import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const env = (globalThis as typeof globalThis & {
  process?: { env?: Record<string, string | undefined> };
}).process?.env;

const backendProxy = {
  target: env?.NOESIS_API_PROXY_TARGET ?? "http://localhost:8000",
  changeOrigin: true
};

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/positions": backendProxy,
      "/runs": backendProxy,
      "/entities": backendProxy,
      "/evidences": backendProxy,
      "/theses": backendProxy,
      "/segments": backendProxy,
      "/portfolio": backendProxy
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts"
  }
});
