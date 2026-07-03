import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { PortfolioHome } from "./PortfolioHome";
import { makeBrief, makePosition } from "./PortfolioHome.test-fixtures";
import type { ResolvePositionResult } from "../../types/api";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  resolvePosition: vi.fn(),
  startRun: vi.fn()
}));

const listPositionsMock = vi.mocked(client.listPositions);
const createPositionMock = vi.mocked(client.createPosition);
const resolvePositionMock = vi.mocked(client.resolvePosition);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);

function makeResolution(
  overrides: Partial<ResolvePositionResult> = {}
): ResolvePositionResult {
  return {
    status: "resolved",
    name: "Tesla, Inc.",
    symbol: "TSLA",
    market: "US",
    node_type: "company",
    existing_position_id: null,
    existing_position_label: null,
    ...overrides
  };
}

async function openFormAndSubmit(name: string): Promise<void> {
  fireEvent.click(await screen.findByRole("button", { name: "+ 添加持仓" }));
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: name } });
  fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
}

describe("PortfolioHome position entry confirmation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    getSharedSuppliersMock.mockResolvedValue([]);
    listPositionsMock.mockResolvedValue([]);
  });

  it("resolves the input and creates the position after confirmation", async () => {
    resolvePositionMock.mockResolvedValue(makeResolution());
    createPositionMock.mockResolvedValue(makePosition({ symbol: "TSLA" }));

    render(<PortfolioHome />);
    await openFormAndSubmit("tesla");

    await waitFor(() =>
      expect(resolvePositionMock).toHaveBeenCalledWith({
        symbol: null,
        market: "US",
        name: "tesla",
        kind: "owned"
      })
    );
    const confirmBar = await screen.findByLabelText("录入确认");
    expect(within(confirmBar).getByText(/Tesla, Inc\./)).toBeInTheDocument();
    expect(within(confirmBar).getByText(/TSLA · US/)).toBeInTheDocument();

    fireEvent.click(within(confirmBar).getByRole("button", { name: "确认添加" }));

    await waitFor(() =>
      expect(createPositionMock).toHaveBeenCalledWith({
        symbol: "TSLA",
        market: "US",
        name: "Tesla, Inc.",
        kind: "owned"
      })
    );
    await waitFor(() =>
      expect(screen.queryByLabelText("录入确认")).not.toBeInTheDocument()
    );
  });

  it("shows existing position and does not create a duplicate", async () => {
    resolvePositionMock.mockResolvedValue(
      makeResolution({
        existing_position_id: "position-1",
        existing_position_label: "TSLA"
      })
    );

    render(<PortfolioHome />);
    await openFormAndSubmit("tesla");

    const confirmBar = await screen.findByLabelText("录入确认");
    expect(within(confirmBar).getByText(/已在组合中/)).toBeInTheDocument();
    expect(
      within(confirmBar).queryByRole("button", { name: "确认添加" })
    ).not.toBeInTheDocument();

    fireEvent.click(within(confirmBar).getByRole("button", { name: "知道了" }));

    expect(screen.queryByLabelText("录入确认")).not.toBeInTheDocument();
    expect(createPositionMock).not.toHaveBeenCalled();
  });

  it("offers force-create when the input cannot be resolved", async () => {
    resolvePositionMock.mockResolvedValue(
      makeResolution({
        status: "unresolved",
        name: "somecorp",
        symbol: null,
        node_type: null
      })
    );
    createPositionMock.mockResolvedValue(
      makePosition({ symbol: "", name: "somecorp" })
    );

    render(<PortfolioHome />);
    await openFormAndSubmit("somecorp");

    const confirmBar = await screen.findByLabelText("录入确认");
    expect(within(confirmBar).getByText(/未能识别/)).toBeInTheDocument();

    fireEvent.click(
      within(confirmBar).getByRole("button", { name: "仍按原样添加" })
    );

    await waitFor(() =>
      expect(createPositionMock).toHaveBeenCalledWith({
        symbol: null,
        market: "US",
        name: "somecorp",
        kind: "owned"
      })
    );
  });

  it("cancels the confirmation without creating anything", async () => {
    resolvePositionMock.mockResolvedValue(makeResolution());

    render(<PortfolioHome />);
    await openFormAndSubmit("tesla");

    const confirmBar = await screen.findByLabelText("录入确认");
    fireEvent.click(within(confirmBar).getByRole("button", { name: "取消" }));

    expect(screen.queryByLabelText("录入确认")).not.toBeInTheDocument();
    expect(createPositionMock).not.toHaveBeenCalled();
  });
});
