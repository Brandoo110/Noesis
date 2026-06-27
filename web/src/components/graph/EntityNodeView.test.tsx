import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { describe, expect, it, vi } from "vitest";

import type { EntityNode } from "../../types/api";
import { EntityNodeView } from "./EntityNodeView";

describe("EntityNodeView", () => {
  it("visually distinguishes seed and node type", () => {
    renderNode(
      <EntityNodeView
        data={{
          entity: makeEntity({ node_type: "company" }),
          expanded: false,
          isSeed: true,
          onExpand: vi.fn()
        }}
        dragging={false}
        id="entity-aapl"
        isConnectable={false}
        selected={false}
        type="entity"
        xPos={0}
        yPos={0}
        zIndex={0}
      />
    );

    const node = screen.getByTestId("entity-node-entity-aapl");
    expect(node).toHaveClass("node-company");
    expect(node).toHaveClass("node-seed");
    expect(node).toHaveStyle({ borderWidth: "2px" });
  });

  it("renders source and target handles for React Flow edges", () => {
    renderNode(
      <EntityNodeView
        data={{
          entity: makeEntity({ node_type: "company" }),
          expanded: false,
          isSeed: false,
          onExpand: vi.fn()
        }}
        dragging={false}
        id="entity-aapl"
        isConnectable={false}
        selected={false}
        type="entity"
        xPos={0}
        yPos={0}
        zIndex={0}
      />
    );

    expect(screen.getByTestId("source-handle-entity-aapl")).toBeInTheDocument();
    expect(screen.getByTestId("target-handle-entity-aapl")).toBeInTheDocument();
  });
});

function renderNode(node: JSX.Element): void {
  render(<ReactFlowProvider>{node}</ReactFlowProvider>);
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
