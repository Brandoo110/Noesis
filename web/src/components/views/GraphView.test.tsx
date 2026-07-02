import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { EvidenceDrawer } from "../evidence/EvidenceDrawer";
import { EvidenceDrawerProvider } from "../../context/evidence-drawer";
import { makeEdge, makeEntity, makeEvidence, makeExpandResult, makeRunDetail } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { Edge } from "../../types/api";
import { GraphView } from "./GraphView";

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

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn(),
  getEvidence: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getRelevance: vi.fn(),
  getRun: vi.fn()
}));

interface FlowProps {
  edgeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  edges: Array<{ id: string; type?: string; data: { edge: Edge } }>;
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

const expandEntityMock = vi.mocked(client.expandEntity);
const getEvidenceMock = vi.mocked(client.getEvidence);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getRunMock = vi.mocked(client.getRun);

describe("GraphView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    getRunMock.mockResolvedValue(makeRunDetail(seed, makeEvidence()));
    getNeighborsMock.mockResolvedValue({ entity_id: seed.id, edges: [] });
    getOverlapsMock.mockResolvedValue([]);
    getRelevanceMock.mockResolvedValue({
      entity_id: seed.id,
      position_id: "position-1",
      path: [seed]
    });
  });

  it("uses the selected seed snapshot for lazy graph detail and evidence", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const sourceNeighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    const inferredNeighbor = makeEntity({
      id: "segment-consumer",
      name: "Consumer Electronics",
      node_type: "segment",
      symbol: null
    });
    expandEntityMock.mockResolvedValue(makeExpandResult([
      makeEdge("edge-source", sourceNeighbor, "source_backed", ["evidence-1"]),
      makeEdge("edge-inferred", inferredNeighbor, "inferred", [])
    ]));

    renderGraph(<GraphView seed={{ positionId: "position-1", runId: "run-1", seedEntity: seed }} />);

    expect(screen.getByTestId("graph-node-entity-aapl")).toHaveTextContent("AAPL");
    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(await screen.findByRole("heading", { name: "分类情报流" })).toBeInTheDocument();
    expect(expandEntityMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "展开 Apple Inc." }));
    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(screen.getByTestId("edge-path-edge-source")).toHaveClass("edge-source-backed");
    expect(screen.getByTestId("edge-path-edge-inferred")).toHaveClass("edge-inferred");

    fireEvent.click(screen.getByRole("button", { name: "source_backed" }));
    expect(screen.getByTestId("edge-path-edge-source")).toBeInTheDocument();
    expect(screen.queryByTestId("edge-path-edge-inferred")).not.toBeInTheDocument();
    expect(expandEntityMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(expandEntityMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));
    expect(screen.getByRole("heading", { name: "Thesis" })).toBeInTheDocument();
    fireEvent.click(
      within(screen.getByLabelText("情报 Supplier update")).getByRole("button", {
        name: "查看证据"
      })
    );
    expect(await screen.findByRole("dialog", { name: "证据抽屉" })).toHaveTextContent(
      "Supplier pressure eased."
    );
    expect(getEvidenceMock).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("renders an empty state before a portfolio seed is selected", () => {
    renderGraph(<GraphView seed={null} />);

    expect(screen.getByRole("heading", { name: "选择一个持仓进入图谱" })).toBeInTheDocument();
  });
});

function renderGraph(node: JSX.Element): ReturnType<typeof render> {
  return render(
    <EvidenceDrawerProvider>
      {node}
      <EvidenceDrawer />
    </EvidenceDrawerProvider>
  );
}
