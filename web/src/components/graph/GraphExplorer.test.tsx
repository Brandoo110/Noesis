import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type { Edge, EntityNode, ExpandResult } from "../../types/api";
import { GraphExplorer } from "./GraphExplorer";

vi.mock("reactflow", async () => {
  const React = await import("react");
  return {
    default: ({
      nodes,
      nodeTypes
    }: {
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
      </div>
    ),
    Background: () => null,
    Controls: () => null,
    ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
  };
});

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("GraphExplorer", () => {
  it("starts with the seed node and lazily expands clicked node", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const neighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-aapl-tsm", neighbor)
    ]));

    render(<GraphExplorer positionId="position-1" seedEntity={seed} />);

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开" }));

    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(await screen.findByText("TSM")).toBeInTheDocument();
  });
});

function makeExpandResult(entityId: string, edges: Edge[]): ExpandResult {
  return {
    entity_id: entityId,
    run_id: `run-${entityId}`,
    status: "completed",
    edges
  };
}

function makeEdge(id: string, neighbor: EntityNode): Edge {
  return {
    id,
    to_entity_id: neighbor.id,
    to_name: neighbor.name,
    to_symbol: neighbor.symbol,
    relation: "supplier",
    basis: "source_backed",
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
