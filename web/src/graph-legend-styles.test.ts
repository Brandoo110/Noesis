import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const css = fs.readFileSync(path.resolve(__dirname, "styles/part-04.css"), "utf8");

describe("graph legend styles", () => {
  it("aligns the graph legend with the status note as a rounded panel", () => {
    expect(css).toMatch(/\.graph-legend\s*\{[\s\S]*margin:\s*8px 18px 0;/);
    expect(css).toMatch(/\.graph-legend\s*\{[\s\S]*border:\s*1px solid var\(--line-2\);/);
    expect(css).toMatch(/\.graph-legend\s*\{[\s\S]*border-radius:\s*10px;/);
  });

  it("keeps relation legend and zoom controls outside the scrolling graph layer", () => {
    expect(css).toMatch(/\.graph-canvas\s*\{[\s\S]*overflow:\s*hidden;/);
    expect(css).toMatch(/\.graph-canvas\s*\{[\s\S]*height:\s*var\(--graph-canvas-h,\s*560px\);/);
    expect(css).toMatch(/\.graph-scroll-plane\s*\{[\s\S]*overflow-x:\s*auto;/);
    expect(css).toMatch(/\.graph-scroll-plane\s*\{[\s\S]*height:\s*100%;/);
    expect(css).toMatch(/\.relation-legend\s*\{[\s\S]*left:\s*14px;/);
    expect(css).toMatch(/\.relation-legend\s*\{[\s\S]*right:\s*auto;/);
    expect(css).toMatch(/\.graph-zoom-controls\s*\{/);
  });
});
