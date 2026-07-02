import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { REDLINE_PATTERN } from "./test/redline";

describe("App V1.5 graph basis path", () => {
  it("links basis filtering across the graph canvas and relationship table", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 NVDA" }));
    const relationships = screen.getByLabelText("关系清单");
    expect(within(relationships).getAllByText("source").length).toBeGreaterThan(0);
    expect(within(relationships).getAllByText("inferred").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "inferred" }));
    expect(within(relationships).queryByText("source")).not.toBeInTheDocument();
    expect(within(relationships).getAllByText("inferred").length).toBeGreaterThan(0);
    expect(screen.getByText("工业富联")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "source_backed" }));
    expect(within(relationships).queryByText("inferred")).not.toBeInTheDocument();
    expect(within(relationships).getAllByText("source").length).toBeGreaterThan(0);

    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});
