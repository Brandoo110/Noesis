import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { REDLINE_PATTERN } from "../../test/redline";
import type { CorrelationMatrix as CorrelationMatrixData } from "../../types/api";
import { CorrelationMatrix } from "./CorrelationMatrix";

vi.mock("../../api/client", () => ({
  getCorrelationMatrix: vi.fn()
}));

const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);

describe("CorrelationMatrix", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders top shared-supplier pairs and opens the full matrix on demand", async () => {
    getCorrelationMatrixMock.mockResolvedValue(makeMatrix());

    render(<CorrelationMatrix />);

    const panel = await screen.findByTestId("correlation-matrix-panel");

    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(within(panel).getByText("AAPL / Microsoft")).toBeInTheDocument();
    expect(within(panel).getByText("2 个共享上游")).toBeInTheDocument();
    expect(within(panel).getByText("TSMC、Samsung")).toBeInTheDocument();
    expect(screen.queryByTestId("correlation-matrix-scroll")).not.toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: "查看矩阵" }));

    const dialog = await screen.findByRole("dialog", { name: "供应链相关性矩阵" });
    const sharedCell = await screen.findByTestId(
      "correlation-cell-position-aapl-position-msft"
    );
    const diagonalCell = screen.getByTestId("correlation-cell-position-aapl-position-aapl");

    expect(within(dialog).getAllByText("AAPL")).toHaveLength(2);
    expect(within(dialog).getAllByText("Microsoft")).toHaveLength(2);
    expect(sharedCell).toHaveTextContent("2");
    const sharedButton = within(sharedCell).getByRole("button", { name: "2" });
    expect(sharedButton.getAttribute("style")).toContain("rgba(76, 84, 92");
    expect(sharedButton.getAttribute("style")).not.toMatch(/red|green/i);
    expect(diagonalCell).toHaveTextContent("");

    fireEvent.click(sharedButton);

    expect(within(panel).getByText("TSMC")).toBeInTheDocument();
    expect(within(panel).getByText("Samsung")).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("shows an empty state for a single holding", async () => {
    getCorrelationMatrixMock.mockResolvedValue({
      positions: [{ position_id: "position-aapl", symbol: "AAPL", label: "AAPL" }],
      cells: []
    });

    render(<CorrelationMatrix />);

    expect(await screen.findByText("持仓不足，暂无相关性")).toBeInTheDocument();
  });

  it("keeps large matrices inside a scroll viewport", async () => {
    getCorrelationMatrixMock.mockResolvedValue(makeLargeMatrix());

    render(<CorrelationMatrix />);

    const panel = await screen.findByTestId("correlation-matrix-panel");

    expect(within(panel).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByTestId("correlation-matrix-scroll")).not.toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: "查看矩阵" }));

    const viewport = await screen.findByTestId("correlation-matrix-scroll");
    const table = within(viewport).getByRole("table", { name: "供应链相关性" });

    expect(viewport).toHaveClass("matrix-scroll");
    expect(table).toHaveAttribute("data-axis-count", "2");
    expect(within(table).queryByText("GOOGL")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "显示全部持仓" }));

    const fullTable = within(viewport).getByRole("table", { name: "供应链相关性" });

    expect(fullTable).toHaveAttribute("data-axis-count", "20");
    expect(within(fullTable).getAllByText("GOOGL").length).toBeGreaterThan(1);
  });
});

function makeMatrix(): CorrelationMatrixData {
  return {
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", label: "AAPL" },
      { position_id: "position-msft", symbol: null, label: "Microsoft" }
    ],
    cells: [
      {
        a_position_id: "position-aapl",
        b_position_id: "position-msft",
        shared_count: 2,
        shared_suppliers: ["TSMC", "Samsung"]
      }
    ]
  };
}

function makeLargeMatrix(): CorrelationMatrixData {
  const symbols = [
    "AAPL",
    "MSFT",
    "SONY",
    "tesla",
    "AMD",
    "AMZN",
    "ASML",
    "BABA",
    "COST",
    "DIS",
    "GOOGL",
    "JPM",
    "META",
    "NFLX",
    "NKE",
    "NVDA",
    "PFE",
    "TM",
    "TSLA",
    "XOM"
  ];
  return {
    positions: symbols.map((symbol) => ({
      position_id: `position-${symbol.toLowerCase()}`,
      symbol,
      label: symbol
    })),
    cells: [
      {
        a_position_id: "position-aapl",
        b_position_id: "position-msft",
        shared_count: 1,
        shared_suppliers: ["TSMC"]
      }
    ]
  };
}
