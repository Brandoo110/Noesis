import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
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

vi.mock("reactflow", async () => ({
  default: ({
    edgeTypes,
    edges,
    nodeTypes,
    nodes
  }: {
    edgeTypes: Record<string, ComponentType<Record<string, unknown>>>;
    edges: Array<{ id: string; source: string; target: string; type?: string; data: unknown }>;
    nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
    nodes: Array<{ id: string; type?: string; data: unknown }>;
  }) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return (
          <Node
            data={node.data}
            dragging={false}
            id={node.id}
            isConnectable={false}
            key={node.id}
            selected={false}
            type={node.type}
            xPos={0}
            yPos={0}
            zIndex={0}
          />
        );
      })}
      <svg aria-label="graph edges">
        {edges.map((edge, index) => {
          const EdgeView = edgeTypes[edge.type ?? "edge"];
          return (
            <EdgeView
              data={edge.data}
              id={edge.id}
              key={edge.id}
              markerEnd=""
              selected={false}
              source={edge.source}
              sourceX={0}
              sourceY={index * 40}
              target={edge.target}
              targetX={100}
              targetY={index * 40}
            />
          );
        })}
      </svg>
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  getBezierPath: () => ["M0,0 L10,10", 5, 5],
  Handle: ({
    "data-testid": testId,
    type
  }: {
    "data-testid"?: string;
    type: string;
  }) => <span data-testid={testId} data-type={type} />,
  Position: {
    Left: "left",
    Right: "right"
  },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  confirmThesis: vi.fn(),
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getEvidence: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRepresentatives: vi.fn(),
  getRun: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

const confirmThesisMock = vi.mocked(client.confirmThesis);
const createPositionMock = vi.mocked(client.createPosition);
const expandEntityMock = vi.mocked(client.expandEntity);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getEvidenceMock = vi.mocked(client.getEvidence);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const getRunMock = vi.mocked(client.getRun);
const listPositionsMock = vi.mocked(client.listPositions);
const startRunMock = vi.mocked(client.startRun);
let consoleErrorMock: ReturnType<typeof vi.spyOn>;

describe("App M3 integration path", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    consoleErrorMock = vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleErrorMock.mockRestore();
  });

  it("walks portfolio research, lazy graph, detail, confirm, and evidence drawer", async () => {
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
    const createdPosition = makePosition();
    const sourceBacked = makeEdge("edge-source", tsm, "source_backed", ["evidence-1"]);
    const inferred = makeEdge("edge-inferred", segment, "inferred", []);

    listPositionsMock.mockImplementation(async () => positions);
    createPositionMock.mockImplementation(async () => {
      positions = [createdPosition];
      return createdPosition;
    });
    startRunMock.mockResolvedValue({
      run_id: "run-1",
      status: "awaiting_confirmation",
      thesis_id: "thesis-1"
    });
    getRunMock.mockResolvedValue(makeRunDetail(aapl, evidence));
    expandEntityMock.mockResolvedValue(makeExpandResult([sourceBacked, inferred]));
    getNeighborsMock.mockResolvedValue({ entity_id: "entity-aapl", edges: [sourceBacked] });
    getOverlapsMock.mockResolvedValue([makeOverlapGroup()]);
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getSharedSuppliersMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue({
      generated_at: "2026-06-28T00:00:00Z",
      positions: [],
      overlaps: [],
      run_health: makeRunHealth()
    });
    getRelevanceMock.mockResolvedValue({
      entity_id: "entity-aapl",
      position_id: "position-1",
      path: [aapl, tsm]
    });
    confirmThesisMock.mockResolvedValue({
      run_id: "run-1",
      status: "completed",
      thesis_id: "thesis-1"
    });

    render(<App />);

    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Apple" } });
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));

    await waitFor(() => expect(createPositionMock).toHaveBeenCalled());
    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    expect(await screen.findByText("Consumer Electronics")).toBeInTheDocument();
    expect(screen.getByText("基于推断")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    expect(
      await screen.findByRole("button", { name: "查看图谱 AAPL" })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 AAPL" }));
    expect(screen.getByTestId("entity-node-entity-aapl")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开" }));
    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(expandEntityMock).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("TSM")).toBeInTheDocument();
    expect(screen.getByTestId("entity-node-segment-consumer")).toHaveTextContent(
      "Consumer Electronics"
    );
    expect(screen.getByTestId("edge-path-edge-source")).toHaveClass(
      "edge-source-backed"
    );
    expect(screen.getByTestId("edge-path-edge-inferred")).toHaveClass(
      "edge-inferred"
    );
    fireEvent.click(screen.getByRole("button", { name: "已展开" }));
    expect(expandEntityMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "详情 AAPL" }));
    expect(screen.queryByRole("button", { name: "详情 TSM" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "现状一句话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "分类情报流" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "产业链位置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "和持仓关系" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Thesis" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "关注点" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "确认 thesis 假设" }));
    await waitFor(() =>
      expect(confirmThesisMock).toHaveBeenCalledWith("thesis-1", {
        status: "confirmed"
      })
    );
    expect(getRunMock).toHaveBeenCalledTimes(4);

    fireEvent.click(
      within(screen.getByLabelText("情报 Supplier update")).getByRole("button", {
        name: "查看证据"
      })
    );
    const drawer = await screen.findByRole("dialog", { name: "证据抽屉" });
    expect(within(drawer).getByText("Supplier pressure eased.")).toBeInTheDocument();
    expect(within(drawer).getByText("tier 2")).toBeInTheDocument();
    expect(within(drawer).getByRole("link", { name: "打开来源" })).toHaveAttribute(
      "href",
      "https://example.com/evidence-1"
    );
    expect(getEvidenceMock).not.toHaveBeenCalled();
    fireEvent.click(within(drawer).getByRole("button", { name: "关闭" }));
    expect(screen.queryByRole("dialog", { name: "证据抽屉" })).not.toBeInTheDocument();

    const attention = screen.getByLabelText("关注点列表");
    expect(attention.tagName.toLowerCase()).toBe("small");
    expect(within(attention).getByText("仅供参考")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
    expect(consoleErrorMock).not.toHaveBeenCalled();
  });
});
