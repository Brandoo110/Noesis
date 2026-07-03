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

  it("renders shared supplier counts with neutral styling and supplier details", async () => {
    getCorrelationMatrixMock.mockResolvedValue(makeMatrix());

    render(<CorrelationMatrix />);

    const panel = await screen.findByTestId("correlation-matrix-panel");
    const sharedCell = await screen.findByTestId(
      "correlation-cell-position-aapl-position-msft"
    );
    const diagonalCell = screen.getByTestId("correlation-cell-position-aapl-position-aapl");

    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(within(panel).getAllByText("AAPL")).toHaveLength(2);
    expect(within(panel).getAllByText("Microsoft")).toHaveLength(2);
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

    const viewport = await screen.findByTestId("correlation-matrix-scroll");
    const table = within(viewport).getByRole("table", { name: "供应链相关性" });

    expect(viewport).toHaveClass("matrix-scroll");
    expect(table).toHaveAttribute("data-axis-count", "20");
    expect(within(table).getAllByText("GOOGL").length).toBeGreaterThan(1);
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
