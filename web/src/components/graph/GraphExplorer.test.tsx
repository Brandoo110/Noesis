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
    onClose?: () => void;
    positionId: string;
    runId: string;
  }) => (
    <aside aria-label="个股详情" role="dialog">
      {`${entityId}:${positionId}:${runId}`}
    </aside>
  )
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("GraphExplorer", () => {
  it("opens detail from the seed node and expands through the seed badge", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const neighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-aapl-tsm", neighbor)
    ]));

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    expect(screen.getByTestId("graph-stage")).toBeInTheDocument();
    expect(screen.queryByTestId("react-flow")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-node-entity-aapl")).toHaveClass("seed-node");
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(screen.getByRole("dialog", { name: "个股详情" })).toHaveTextContent(
      "entity-aapl:position-1:run-1"
    );
    expect(expandEntityMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "展开 Apple Inc." }));

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

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    fireEvent.click(screen.getByRole("button", { name: "展开 Apple Inc." }));
    expect(await screen.findByTestId("edge-path-edge-source")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-inferred")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "source_backed" }));

    expect(screen.getByTestId("edge-path-edge-source")).toBeInTheDocument();
    expect(screen.queryByTestId("edge-path-edge-inferred")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重置图谱" }));
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();
    expect(screen.queryByText("Consumer Electronics")).not.toBeInTheDocument();
  });

  it("opens stock detail in an overlay and closes it from the backdrop", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });

    const { container } = renderGraph(
      <GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />
    );

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));

    expect(screen.getByRole("dialog", { name: "个股详情" })).toHaveTextContent(
      "entity-aapl:position-1:run-1"
    );
    const backdrop = container.querySelector(".detail-layer .drawer-backdrop");
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop as Element);
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "个股详情" })).not.toBeInTheDocument()
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
