import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const css = fs.readFileSync(path.resolve(__dirname, "styles/part-09.css"), "utf8");

describe("AgentOps layout styles", () => {
  it("sizes run panels from the viewport and contains internal scroll chaining", () => {
    expect(css).toContain("--ops-panel-height");
    expect(css).toContain("calc(100vh - 90px)");
    expect(css).toMatch(/\.ops-runs,\s*\.run-trace\s*\{[\s\S]*height:\s*var\(--ops-panel-height\)/);
    expect(css).toMatch(/\.ops-runs ul,\s*\.run-trace ol\s*\{[\s\S]*overscroll-behavior:\s*contain/);
  });
});
