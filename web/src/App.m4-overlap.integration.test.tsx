import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { REDLINE_PATTERN } from "./test/redline";

describe("App portfolio overlap path", () => {
  it("surfaces portfolio brief overlaps and correlation matrix in the redesigned home", () => {
    render(<App />);

    const brief = screen.getByLabelText("组合 Brief");
    expect(within(brief).getByText("AI 加速计算")).toBeInTheDocument();
    expect(within(brief).getByText("半导体设备")).toBeInTheDocument();
    expect(within(brief).getAllByText("有出处").length).toBeGreaterThan(0);
    expect(within(brief).getByText("基于推断")).toBeInTheDocument();

    const matrix = screen.getByLabelText("相关性矩阵");
    expect(within(matrix).getAllByText("NVDA").length).toBeGreaterThan(0);
    expect(within(matrix).getAllByText(".72").length).toBe(2);
    expect(within(matrix).getAllByText(".66").length).toBe(2);

    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});
