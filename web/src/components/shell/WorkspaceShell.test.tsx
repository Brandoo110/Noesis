import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "./WorkspaceShell";

const seed = {
  positionId: "position-1",
  runId: "run-1",
  seedEntity: {
    id: "entity-aapl",
    market: "US",
    name: "Apple Inc.",
    node_type: "company",
    symbol: "AAPL"
  }
};

vi.mock("../views/PortfolioView", () => ({
  PortfolioView: ({
    onGraphSeedSelected
  }: {
    onGraphSeedSelected?: (nextSeed: typeof seed) => void;
  }) => (
    <section aria-label="组合首页">
      portfolio content
      <button onClick={() => onGraphSeedSelected?.(seed)} type="button">
        mock open graph
      </button>
    </section>
  )
}));

vi.mock("../views/GraphView", () => ({
  GraphView: ({ seed: activeSeed }: { seed: typeof seed | null }) => (
    <section aria-label="图谱探索视图">
      <h2>图谱探索</h2>
      <span>{activeSeed?.runId ?? "no seed"}</span>
      <span>{activeSeed?.seedEntity.symbol ?? "no symbol"}</span>
    </section>
  )
}));

vi.mock("../views/AgentOpsView", () => ({
  AgentOpsView: () => <section aria-label="AgentOps视图">mock agentops</section>
}));

describe("WorkspaceShell", () => {
  it("renders three view entries and switches the active workspace", () => {
    render(<WorkspaceShell />);

    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(within(nav).getByRole("button", { name: "组合工作台" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "图谱探索" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "AgentOps" })).toBeInTheDocument();
    const mobileNav = screen.getByRole("navigation", { name: "移动端导航" });
    expect(within(mobileNav).getAllByRole("button")).toHaveLength(3);
    expect(screen.getByLabelText("组合首页")).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: "图谱探索" }));
    expect(
      within(screen.getByLabelText("图谱探索视图")).getByRole("heading", {
        name: "图谱探索"
      })
    ).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: "AgentOps" }));
    expect(screen.getByLabelText("AgentOps视图")).toHaveTextContent("mock agentops");

    fireEvent.click(within(mobileNav).getByRole("button", { name: "组合工作台" }));
    expect(screen.getByLabelText("组合首页")).toBeInTheDocument();
  });

  it("captures graph seed from the portfolio view and opens graph workspace", () => {
    render(<WorkspaceShell />);

    fireEvent.click(screen.getByRole("button", { name: "mock open graph" }));

    const graph = screen.getByLabelText("图谱探索视图");
    expect(within(graph).getByText("run-1")).toBeInTheDocument();
    expect(within(graph).getByText("AAPL")).toBeInTheDocument();
  });

  it("opens topbar health popover and closes it from an outside click", () => {
    render(<WorkspaceShell />);

    fireEvent.click(screen.getByRole("button", { name: "Health" }));
    expect(screen.getByLabelText("产品状态")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText("组合首页"));
    expect(screen.queryByLabelText("产品状态")).not.toBeInTheDocument();
  });
});
