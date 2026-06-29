import { describe, expect, it } from "vitest";

import { edgeClassName, edgeStyle, nodeClassName, nodeStyle } from "./visual";

describe("visual semantics", () => {
  it("keeps node types visually distinct and marks seed nodes", () => {
    expect(nodeClassName("company", false)).toBe("node-company");
    expect(nodeClassName("segment", false)).toBe("node-segment");
    expect(nodeClassName("theme", false)).toBe("node-theme");
    expect(nodeClassName("company", true)).toBe("node-company node-seed");

    expect(nodeStyle("company", false)).toMatchObject({
      backgroundColor: "#ffffff",
      borderColor: "#9fbac9",
      borderRadius: "8px",
      borderStyle: "solid"
    });
    expect(nodeStyle("segment", false)).toMatchObject({
      backgroundColor: "#ffffff",
      borderColor: "#a6c892"
    });
    expect(nodeStyle("theme", false)).toMatchObject({
      backgroundColor: "#ffffff",
      borderColor: "#d9ad73"
    });
    expect(nodeStyle("company", true)).toMatchObject({
      borderColor: "#005155",
      borderWidth: "2px"
    });
  });

  it("keeps inferred edges visually weaker than source-backed edges", () => {
    expect(edgeClassName("source_backed")).toBe("edge-source-backed");
    expect(edgeClassName("inferred")).toBe("edge-inferred");

    expect(edgeStyle("source_backed")).toMatchObject({
      opacity: 0.88,
      stroke: "#005155",
      strokeDasharray: "none"
    });
    expect(edgeStyle("inferred")).toMatchObject({
      opacity: 0.5,
      stroke: "#bec9c9",
      strokeDasharray: "4 4"
    });
  });
});
