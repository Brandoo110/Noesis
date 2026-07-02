import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "./WorkspaceShell";

vi.mock("../views/PortfolioView", () => ({
  PortfolioView: () => <section aria-label="组合首页">portfolio content</section>
}));

describe("WorkspaceShell", () => {
  it("renders three view entries and switches the active workspace", () => {
    render(<WorkspaceShell />);

    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(within(nav).getByRole("button", { name: "组合工作台" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "图谱探索" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "AgentOps" })).toBeInTheDocument();
    expect(screen.getByLabelText("组合首页")).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: "图谱探索" }));
    expect(
      within(screen.getByLabelText("图谱探索视图")).getByRole("heading", {
        name: "图谱探索"
      })
    ).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: "AgentOps" }));
    expect(
      within(screen.getByLabelText("AgentOps视图")).getByRole("heading", {
        name: "AgentOps"
      })
    ).toBeInTheDocument();
  });
});
