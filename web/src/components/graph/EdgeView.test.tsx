import { render, screen } from "@testing-library/react";
import { Position } from "reactflow";
import { describe, expect, it } from "vitest";

import type { Edge } from "../../types/api";
import { EdgeView } from "./EdgeView";

describe("EdgeView", () => {
  it("renders source-backed edges as solid", () => {
    render(
      <svg>
        <EdgeView
          data={{ edge: makeEdge({ basis: "source_backed" }) }}
          id="edge-1"
          markerEnd=""
          selected={false}
          source="entity-aapl"
          sourcePosition={Position.Right}
          sourceX={0}
          sourceY={0}
          target="entity-tsm"
          targetPosition={Position.Left}
          targetX={100}
          targetY={0}
        />
      </svg>
    );

    const edgePath = screen.getByTestId("edge-path-edge-1");
    expect(edgePath).toHaveClass("edge-source-backed");
    expect(edgePath).toHaveStyle({ strokeDasharray: "none", opacity: "1" });
    expect(screen.getByText("supplier 82%")).toBeInTheDocument();
  });

  it("renders inferred edges as dashed and translucent", () => {
    render(
      <svg>
        <EdgeView
          data={{ edge: makeEdge({ basis: "inferred" }) }}
          id="edge-2"
          markerEnd=""
          selected={false}
          source="entity-aapl"
          sourcePosition={Position.Right}
          sourceX={0}
          sourceY={0}
          target="segment-consumer"
          targetPosition={Position.Left}
          targetX={100}
          targetY={0}
        />
      </svg>
    );

    const edgePath = screen.getByTestId("edge-path-edge-2");
    expect(edgePath).toHaveClass("edge-inferred");
    expect(edgePath).toHaveStyle({ strokeDasharray: "6 4", opacity: "0.55" });
  });
});

function makeEdge(overrides: Partial<Edge> = {}): Edge {
  return {
    id: "edge-1",
    to_entity_id: "entity-tsm",
    to_name: "TSMC",
    to_symbol: "TSM",
    relation: "supplier",
    basis: "source_backed",
    confidence: 0.82,
    evidence_ids: ["evidence-1"],
    source_tier: 2,
    rationale: "Supplier relation is source-backed.",
    neighbor: {
      id: "entity-tsm",
      name: "TSMC",
      node_type: "company",
      symbol: "TSM",
      market: "US"
    },
    ...overrides
  };
}
