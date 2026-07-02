import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "./test/agentops-fixtures";
import { makeEntity, makePosition, makeRunHealth } from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";
import type { SharedSupplierGroup } from "./types/api";

vi.mock("reactflow", () => ({
  default: () => <div data-testid="react-flow" />,
  Background: () => null,
  Controls: () => null,
  getBezierPath: () => ["M0,0 L10,10", 5, 5],
  Handle: ({ "data-testid": testId }: { "data-testid"?: string }) => (
    <span data-testid={testId} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getMetricsSummary: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  listRuns: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);
const listRunsMock = vi.mocked(client.listRuns);

describe("App V1.5 supply chain path", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("expands researched seeds into shared suppliers and correlation", async () => {
    render(<App />);

    await screen.findByRole("button", { name: "分析组合供应链" });
    fireEvent.click(screen.getByRole("button", { name: "分析组合供应链" }));

    await waitFor(() => expect(expandEntityMock).toHaveBeenCalledTimes(2));
    expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-aapl");
    expect(expandEntityMock).toHaveBeenCalledWith("entity-msft", "position-msft");

    const sharedPanel = await screen.findByTestId("shared-suppliers-panel");
    expect(within(sharedPanel).getByText("Taiwan Semiconductor")).toBeInTheDocument();
    expect(within(sharedPanel).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("correlation-cell-position-aapl-position-msft")).getByText("1")
    ).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});

function setupMocks(): void {
  const aapl = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const msft = makeEntity({ id: "entity-msft", name: "Microsoft", symbol: "MSFT" });
  const expanded = new Set<string>();
  listPositionsMock.mockResolvedValue([
    makePosition({
      id: "position-aapl",
      latest_run_entity: aapl,
      latest_run_id: "run-aapl",
      latest_run_status: "completed"
    }),
    makePosition({
      id: "position-msft",
      name: "Microsoft",
      symbol: "MSFT",
      latest_run_entity: msft,
      latest_run_id: "run-msft",
      latest_run_status: "completed"
    })
  ]);
  expandEntityMock.mockImplementation(async (entityId, positionId) => {
    expanded.add(`${positionId}:${entityId}`);
    return { entity_id: entityId, run_id: "run-expand", status: "completed", edges: [] };
  });
  getSharedSuppliersMock.mockImplementation(async () =>
    expanded.size >= 2 ? [makeSharedSupplier()] : []
  );
  getCorrelationMatrixMock.mockImplementation(async () =>
    expanded.size >= 2
      ? {
          positions: [
            { position_id: "position-aapl", symbol: "AAPL", label: "Apple" },
            { position_id: "position-msft", symbol: "MSFT", label: "Microsoft" }
          ],
          cells: [{
            a_position_id: "position-aapl",
            b_position_id: "position-msft",
            shared_count: 1,
            shared_suppliers: ["Taiwan Semiconductor"]
          }]
        }
      : { positions: [], cells: [] }
  );
  getOverlapsMock.mockResolvedValue([]);
  getPortfolioBriefMock.mockResolvedValue({
    generated_at: "2026-07-03T00:00:00Z",
    positions: [],
    overlaps: [],
    run_health: makeRunHealth({ total_latest_runs: 2 })
  });
  listRunsMock.mockResolvedValue(makeAgentOpsRunList());
  getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
  getRunTraceMock.mockResolvedValue(makeRunTrace());
}

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
