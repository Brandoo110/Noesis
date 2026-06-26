import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const backendProxy = {
  target: "http://localhost:8000",
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
      "/segments": backendProxy
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts"
  }
});
