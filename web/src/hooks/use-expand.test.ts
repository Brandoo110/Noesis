import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import type { Edge, EntityNode, ExpandResult } from "../types/api";
import { useExpand } from "./use-expand";

vi.mock("../api/client", () => ({
  expandEntity: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("useExpand", () => {
  it("expands only the clicked node and deduplicates repeated expansions", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const tsm = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    const micron = makeEntity({ id: "entity-mu", name: "Micron", symbol: "MU" });
    expandEntityMock.mockResolvedValueOnce(
      makeExpandResult("entity-aapl", [makeEdge("edge-aapl-tsm", tsm)])
    );
    expandEntityMock.mockResolvedValueOnce(
      makeExpandResult("entity-tsm", [makeEdge("edge-tsm-mu", micron)])
    );

    const { result } = renderHook(() =>
      useExpand({ positionId: "position-1", seedEntity: seed })
    );

    await act(async () => {
      await result.current.expand("entity-aapl");
    });

    expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1");
    expect(result.current.nodes.map((node) => node.id)).toEqual([
      "entity-aapl",
      "entity-tsm"
    ]);
    expect(result.current.edges.map((edge) => edge.id)).toEqual(["edge-aapl-tsm"]);

    await act(async () => {
      await result.current.expand("entity-aapl");
    });
    expect(expandEntityMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.expand("entity-tsm");
    });
    expect(expandEntityMock).toHaveBeenLastCalledWith("entity-tsm", "position-1");
    expect(result.current.nodes.map((node) => node.id)).toEqual([
      "entity-aapl",
      "entity-tsm",
      "entity-mu"
    ]);
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
