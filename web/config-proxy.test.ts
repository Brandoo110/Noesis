// @vitest-environment node

import { describe, expect, it } from "vitest";

import config from "./vite.config";

describe("vite config", () => {
  it("proxies backend API routes to the local FastAPI server", () => {
    const proxy = config.server?.proxy;

    for (const route of [
      "/positions",
      "/runs",
      "/entities",
      "/evidences",
      "/theses",
      "/segments",
      "/portfolio"
    ]) {
      expect(proxy?.[route]).toMatchObject({
        target: "http://localhost:8000",
        changeOrigin: true
      });
    }
  });
});
