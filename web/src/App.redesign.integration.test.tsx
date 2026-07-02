import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "./test/agentops-fixtures";
import { makeRunHealth } from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";

vi.mock("./api/client", () => ({
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getMetricsSummary: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  listRuns: vi.fn(),
  startRun: vi.fn()
}));

const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);
const listRunsMock = vi.mocked(client.listRuns);

describe("App workstation shell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listPositionsMock.mockResolvedValue([]);
    listRunsMock.mockResolvedValue(makeAgentOpsRunList());
    getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
    getRunTraceMock.mockResolvedValue(makeRunTrace());
    getOverlapsMock.mockResolvedValue([]);
    getSharedSuppliersMock.mockResolvedValue([]);
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getPortfolioBriefMock.mockResolvedValue({
      generated_at: "2026-07-03T00:00:00Z",
      positions: [],
      overlaps: [],
      run_health: makeRunHealth()
    });
  });

  it("renders the shell around the real portfolio view and switches workspaces", async () => {
    render(<App />);

    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(within(nav).getByRole("button", { name: "组合工作台" })).toBeInTheDocument();
    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
    expect(getPortfolioBriefMock).toHaveBeenCalled();

    fireEvent.click(within(nav).getByRole("button", { name: "图谱探索" }));
    expect(screen.getByLabelText("图谱探索视图")).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: "AgentOps" }));
    expect(screen.getByLabelText("AgentOps视图")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});
