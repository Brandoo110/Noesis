import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "./test/agentops-fixtures";
import {
  makeEntity,
  makeEvidence,
  makeOverlapGroup,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";

vi.mock("reactflow", () => ({
  default: ({ nodeTypes, nodes }: FlowProps) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return <Node data={node.data} id={node.id} key={node.id} selected={false} />;
      })}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  Handle: ({ "data-testid": testId }: { "data-testid"?: string }) => (
    <span data-testid={testId} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  getCorrelationMatrix: vi.fn(),
  getMetricsSummary: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRun: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  listRuns: vi.fn()
}));

interface FlowProps {
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getRunMock = vi.mocked(client.getRun);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);
const listRunsMock = vi.mocked(client.listRuns);

describe("App M4 overlap path", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("surfaces portfolio overlap hints in home and stock detail", async () => {
    render(<App />);

    const panel = await screen.findByLabelText("组合重叠提示");
    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(await within(panel).findByText("Consumer Electronics")).toBeInTheDocument();
    expect(await within(panel).findByText("AAPL / MSFT")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 MSFT" }));
    fireEvent.click(await screen.findByRole("button", { name: "详情 MSFT" }));
    const detailOverlap = await screen.findByLabelText("组合重叠关系");
    expect(within(detailOverlap).getByText("AAPL")).toBeInTheDocument();
    expect(within(detailOverlap).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});

function setupMocks(): void {
  const aapl = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const msft = makeEntity({ id: "entity-msft", name: "Microsoft", symbol: "MSFT" });
  const overlap = makeOverlapGroup({
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", entity_id: "entity-aapl", confidence: 0.9 },
      { position_id: "position-msft", symbol: "MSFT", entity_id: "entity-msft", confidence: 0.7 }
    ]
  });
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
  getRunMock.mockResolvedValue(makeRunDetail(msft, makeEvidence()));
  getOverlapsMock.mockResolvedValue([overlap]);
  getNeighborsMock.mockResolvedValue({ entity_id: "entity-msft", edges: [] });
  getRelevanceMock.mockResolvedValue({
    entity_id: "entity-msft",
    position_id: "position-msft",
    path: [msft]
  });
  getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
  getSharedSuppliersMock.mockResolvedValue([]);
  getPortfolioBriefMock.mockResolvedValue({
    generated_at: "2026-07-03T00:00:00Z",
    positions: [],
    overlaps: [overlap],
    run_health: makeRunHealth({ total_latest_runs: 2 })
  });
  listRunsMock.mockResolvedValue(makeAgentOpsRunList());
  getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
  getRunTraceMock.mockResolvedValue(makeRunTrace());
}
