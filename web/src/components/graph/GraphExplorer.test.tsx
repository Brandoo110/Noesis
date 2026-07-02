import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { EvidenceDrawerProvider } from "../../context/evidence-drawer";
import type { Edge, EntityNode, ExpandResult } from "../../types/api";
import { GraphExplorer } from "./GraphExplorer";

vi.mock("reactflow", async () => {
  const React = await import("react");
  return {
    default: ({
      edges,
      nodes,
      nodeTypes
    }: {
      edges: Array<{ id: string; data: { edge?: Edge } }>;
      nodes: Array<{ id: string; type?: string; data: unknown }>;
      nodeTypes: Record<string, React.ComponentType<Record<string, unknown>>>;
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
        {edges.map((edge) => (
          <span data-testid={`flow-edge-${edge.id}`} key={edge.id}>
            {edge.data.edge?.basis}
          </span>
        ))}
      </div>
    ),
    Background: () => null,
    Controls: () => null,
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
  };
});

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn()
}));

vi.mock("../stock/StockDetail", () => ({
  StockDetail: ({
    entityId,
    positionId,
    runId
  }: {
    entityId: string;
    positionId: string;
    runId: string;
  }) => <div data-testid="stock-detail">{`${entityId}:${positionId}:${runId}`}</div>
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("GraphExplorer", () => {
  it("starts with the seed node and lazily expands clicked node", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const neighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-aapl-tsm", neighbor)
    ]));

    renderGraph(<GraphExplorer positionId="position-1" seedEntity={seed} />);

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开" }));

    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(await screen.findByText("TSM")).toBeInTheDocument();
    expect(screen.getByLabelText("关系清单")).toHaveTextContent("供应商");
    expect(screen.getByLabelText("关系清单")).toHaveTextContent("82%");
  });

  it("filters visible edges by basis and resets expanded graph", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const sourceNeighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    const inferredNeighbor = makeEntity({
      id: "segment-consumer",
      name: "Consumer Electronics",
      node_type: "segment",
      symbol: null
    });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-source", sourceNeighbor, "source_backed"),
      makeEdge("edge-inferred", inferredNeighbor, "inferred")
    ]));

    renderGraph(<GraphExplorer positionId="position-1" seedEntity={seed} />);

    fireEvent.click(screen.getByRole("button", { name: "展开" }));
    expect(await screen.findByTestId("flow-edge-edge-source")).toBeInTheDocument();
    expect(screen.getByTestId("flow-edge-edge-inferred")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "source_backed" }));

    expect(screen.getByTestId("flow-edge-edge-source")).toBeInTheDocument();
    expect(screen.queryByTestId("flow-edge-edge-inferred")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重置图谱" }));
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();
    expect(screen.queryByText("Consumer Electronics")).not.toBeInTheDocument();
  });

  it("opens stock detail from the seed node when run id is available", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });

    renderGraph(
      <GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />
    );

    fireEvent.click(screen.getByRole("button", { name: "详情 AAPL" }));

    expect(screen.getByTestId("stock-detail")).toHaveTextContent(
      "entity-aapl:position-1:run-1"
    );
  });
});

function renderGraph(graph: JSX.Element): ReturnType<typeof render> {
  return render(<EvidenceDrawerProvider>{graph}</EvidenceDrawerProvider>);
}

function makeExpandResult(entityId: string, edges: Edge[]): ExpandResult {
  return {
    entity_id: entityId,
    run_id: `run-${entityId}`,
    status: "completed",
    edges
  };
}

function makeEdge(
  id: string,
  neighbor: EntityNode,
  basis: Edge["basis"] = "source_backed"
): Edge {
  return {
    id,
    to_entity_id: neighbor.id,
    to_name: neighbor.name,
    to_symbol: neighbor.symbol,
    relation: "supplier",
    basis,
    confidence: 0.82,
    evidence_ids: ["evidence-1"],
    source_tier: 2,
    rationale: "Supplier relation is source-backed.",
    neighbor
  };
}

function makeEntity(overrides: Partial<EntityNode> = {}): EntityNode {
  return {
    id: "entity-aapl",
    name: "Apple Inc.",
    node_type: "company",
    symbol: "AAPL",
    market: "US",
    ...overrides
  };
}
