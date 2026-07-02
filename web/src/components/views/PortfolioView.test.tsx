import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import {
  makeEntity,
  makeEvidence,
  makeOverlapGroup,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "../../test/m3-fixtures";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "../../test/agentops-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { SharedSupplierGroup } from "../../types/api";
import { PortfolioView } from "./PortfolioView";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getMetricsSummary: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listRuns: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

const createPositionMock = vi.mocked(client.createPosition);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRunMock = vi.mocked(client.getRun);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listRunsMock = vi.mocked(client.listRuns);
const listPositionsMock = vi.mocked(client.listPositions);
const startRunMock = vi.mocked(client.startRun);

describe("PortfolioView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRunsMock.mockResolvedValue(makeAgentOpsRunList());
    getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
    getRunTraceMock.mockResolvedValue(makeRunTrace());
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-aapl", symbol: "AAPL", name: "Apple" })
    ]);
    getOverlapsMock.mockResolvedValue([makeOverlapGroup()]);
    getSharedSuppliersMock.mockResolvedValue([makeSharedSupplier()]);
    getCorrelationMatrixMock.mockResolvedValue({
      positions: [
        { position_id: "position-aapl", symbol: "AAPL", label: "Apple" },
        { position_id: "position-msft", symbol: "MSFT", label: "Microsoft" }
      ],
      cells: [
        {
          a_position_id: "position-aapl",
          b_position_id: "position-msft",
          shared_count: 1,
          shared_suppliers: ["Taiwan Semiconductor"]
        }
      ]
    });
    getPortfolioBriefMock.mockResolvedValue({
      generated_at: "2026-07-03T00:00:00Z",
      positions: [],
      overlaps: [],
      run_health: makeRunHealth()
    });
    startRunMock.mockResolvedValue({
      run_id: "run-aapl",
      status: "awaiting_confirmation",
      thesis_id: "thesis-aapl"
    });
    getRunMock.mockResolvedValue(makeRunDetail(makeEntity(), makeEvidence()));
    createPositionMock.mockResolvedValue(
      makePosition({ id: "position-msft", symbol: "MSFT", name: "Microsoft" })
    );
  });

  it("uses the real portfolio client flow for positions research and insights", async () => {
    render(<PortfolioView />);

    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    expect(await screen.findByText("Consumer Electronics")).toBeInTheDocument();
    expect(await screen.findByText("Taiwan Semiconductor")).toBeInTheDocument();
    expect(getOverlapsMock).toHaveBeenCalled();
    expect(getSharedSuppliersMock).toHaveBeenCalled();
    expect(getCorrelationMatrixMock).toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "MSFT" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Microsoft" } });
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
    await waitFor(() => expect(createPositionMock).toHaveBeenCalledWith({
      kind: "owned",
      market: "US",
      name: "Microsoft",
      symbol: "MSFT"
    }));

    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    await waitFor(() => expect(startRunMock).toHaveBeenCalledWith("position-aapl"));
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});

function makeSharedSupplier(): SharedSupplierGroup {
  return {
    supplier_id: "entity-tsmc",
    supplier_name: "Taiwan Semiconductor",
    node_type: "company",
    basis: "source_backed",
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", entity_id: "entity-aapl", confidence: 0.9 },
      { position_id: "position-msft", symbol: "MSFT", entity_id: "entity-msft", confidence: 0.8 }
    ]
  };
}
