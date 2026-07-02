import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  makeEdge,
  makeEntity,
  makeEvidence,
  makeExpandResult,
  makeOverlapGroup,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";
import type { Position } from "./types/api";

vi.mock("reactflow", () => ({
  default: ({ edgeTypes, edges, nodeTypes, nodes }: FlowProps) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return <Node data={node.data} id={node.id} key={node.id} selected={false} />;
      })}
      <svg aria-label="graph edges">
        {edges.map((edge) => {
          const EdgeView = edgeTypes[edge.type ?? "edge"];
          return (
            <EdgeView
              data={edge.data}
              id={edge.id}
              key={edge.id}
              sourceX={0}
              sourceY={0}
              targetX={100}
              targetY={40}
            />
          );
        })}
      </svg>
    </div>
  ),
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
  confirmThesis: vi.fn(),
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getEvidence: vi.fn(),
  getMetricsSummary: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRepresentatives: vi.fn(),
  getRun: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  listRuns: vi.fn(),
  startRun: vi.fn()
}));

interface FlowProps {
  edgeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  edges: Array<{ id: string; source: string; target: string; type?: string; data: unknown }>;
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

const confirmThesisMock = vi.mocked(client.confirmThesis);
const createPositionMock = vi.mocked(client.createPosition);
const expandEntityMock = vi.mocked(client.expandEntity);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getEvidenceMock = vi.mocked(client.getEvidence);
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
const startRunMock = vi.mocked(client.startRun);

describe("App portfolio integration path", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("walks real portfolio data into lazy graph detail and evidence drawer", async () => {
    render(<App />);

    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "+ 添加持仓" }));
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Apple" } });
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
    expect(await screen.findByText("AAPL")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    expect(screen.getByTestId("graph-node-entity-aapl")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(await screen.findByRole("heading", { name: "分类情报流" })).toBeInTheDocument();
    expect(expandEntityMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "展开 Apple Inc." }));
    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(screen.getByTestId("edge-path-edge-source")).toHaveClass("edge-source-backed");
    expect(screen.getByTestId("edge-path-edge-inferred")).toHaveClass("edge-inferred");
    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(expandEntityMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));
    fireEvent.click(
      within(screen.getByLabelText("情报 Supplier update")).getByRole("button", {
        name: "查看证据"
      })
    );
    expect(await screen.findByRole("dialog", { name: "证据抽屉" })).toHaveTextContent(
      "Supplier pressure eased."
    );
    expect(getEvidenceMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "确认 thesis 假设" }));
    await waitFor(() => expect(confirmThesisMock).toHaveBeenCalled());
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});

function setupMocks(): void {
  let positions: Position[] = [];
  const aapl = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const tsm = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
  const segment = makeEntity({
    id: "segment-consumer",
    name: "Consumer Electronics",
    node_type: "segment",
    symbol: null
  });
  const evidence = makeEvidence();

  listPositionsMock.mockImplementation(async () => positions);
  createPositionMock.mockImplementation(async () => {
    positions = [makePosition()];
    return positions[0];
  });
  startRunMock.mockResolvedValue({
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1"
  });
  getRunMock.mockResolvedValue(makeRunDetail(aapl, evidence));
  expandEntityMock.mockResolvedValue(
    makeExpandResult([
      makeEdge("edge-source", tsm, "source_backed", ["evidence-1"]),
      makeEdge("edge-inferred", segment, "inferred", [])
    ])
  );
  getNeighborsMock.mockResolvedValue({ entity_id: "entity-aapl", edges: [] });
  getOverlapsMock.mockResolvedValue([makeOverlapGroup()]);
  getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
  getSharedSuppliersMock.mockResolvedValue([]);
  getPortfolioBriefMock.mockResolvedValue({
    generated_at: "2026-07-03T00:00:00Z",
    positions: [],
    overlaps: [],
    run_health: makeRunHealth()
  });
  getRelevanceMock.mockResolvedValue({
    entity_id: "entity-aapl",
    position_id: "position-1",
    path: [aapl]
  });
  confirmThesisMock.mockResolvedValue({
    run_id: "run-1",
    status: "completed",
    thesis_id: "thesis-1"
  });
  listRunsMock.mockResolvedValue(makeAgentOpsRunList());
  getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
  getRunTraceMock.mockResolvedValue(makeRunTrace());
}
