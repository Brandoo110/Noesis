import { fireEvent, render, screen } from "@testing-library/react";
import { Position } from "reactflow";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { EvidenceDrawer } from "../evidence/EvidenceDrawer";
import { EvidenceDrawerProvider } from "../../context/evidence-drawer";
import type { Edge } from "../../types/api";
import { EdgeView } from "./EdgeView";

vi.mock("../../api/client", () => ({
  getEvidence: vi.fn()
}));

const getEvidenceMock = vi.mocked(client.getEvidence);

describe("EdgeView", () => {
  it("renders source-backed edges as solid", () => {
    render(
      <EvidenceDrawerProvider>
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
      </EvidenceDrawerProvider>
    );

    const edgePath = screen.getByTestId("edge-path-edge-1");
    expect(edgePath).toHaveClass("edge-source-backed");
    expect(edgePath).toHaveStyle({ strokeDasharray: "none", opacity: "1" });
    expect(screen.getByText("supplier 82%")).toBeInTheDocument();
  });

  it("renders inferred edges as dashed and translucent", () => {
    render(
      <EvidenceDrawerProvider>
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
      </EvidenceDrawerProvider>
    );

    const edgePath = screen.getByTestId("edge-path-edge-2");
    expect(edgePath).toHaveClass("edge-inferred");
    expect(edgePath).toHaveStyle({ strokeDasharray: "6 4", opacity: "0.55" });
  });

  it("opens the global evidence drawer from edge evidence ids", async () => {
    getEvidenceMock.mockResolvedValue({
      id: "evidence-1",
      source: "web",
      source_tier: 2,
      url: "https://example.com/evidence-1",
      title: "Supplier evidence",
      snippet: "TSMC supplies Apple.",
      captured_at: "2026-06-27T00:00:00Z",
      published_at: null
    });

    render(
      <EvidenceDrawerProvider>
        <svg>
          <EdgeView
            data={{ edge: makeEdge({ evidence_ids: ["evidence-1"] }) }}
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
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "查看边证据" }));

    expect(
      await screen.findByRole("dialog", { name: "证据抽屉" })
    ).toBeInTheDocument();
    expect(screen.getByText("Supplier evidence")).toBeInTheDocument();
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
