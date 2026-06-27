import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import { makeOverlapGroup } from "../test/m3-fixtures";
import type {
  Edge,
  EntityNode,
  OverlapGroup,
  Relevance,
  RunDetail
} from "../types/api";
import { useStockDetail } from "./use-stock-detail";

vi.mock("../api/client", () => ({
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getRelevance: vi.fn(),
  getRun: vi.fn()
}));

const getRunMock = vi.mocked(client.getRun);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getRelevanceMock = vi.mocked(client.getRelevance);

describe("useStockDetail", () => {
  it("loads run, neighbors and relevance in parallel into one detail shape", async () => {
    const runDeferred = deferred<RunDetail>();
    const neighborsDeferred = deferred<{ entity_id: string; edges: Edge[] }>();
    const relevanceDeferred = deferred<Relevance>();
    const overlapsDeferred = deferred<OverlapGroup[]>();
    getRunMock.mockReturnValue(runDeferred.promise);
    getNeighborsMock.mockReturnValue(neighborsDeferred.promise);
    getRelevanceMock.mockReturnValue(relevanceDeferred.promise);
    getOverlapsMock.mockReturnValue(overlapsDeferred.promise);

    const { result } = renderHook(() =>
      useStockDetail("entity-aapl", "run-1", "position-1")
    );

    await waitFor(() => expect(getRunMock).toHaveBeenCalledWith("run-1"));
    expect(getNeighborsMock).toHaveBeenCalledWith("entity-aapl");
    expect(getRelevanceMock).toHaveBeenCalledWith("entity-aapl", "position-1");
    expect(getOverlapsMock).toHaveBeenCalledWith();
    expect(result.current.isLoading).toBe(true);

    runDeferred.resolve(makeRunDetail());
    neighborsDeferred.resolve({ entity_id: "entity-aapl", edges: [makeEdge()] });
    relevanceDeferred.resolve(makeRelevance());
    overlapsDeferred.resolve([makeOverlapGroup()]);

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.detail).toMatchObject({
      entityId: "entity-aapl",
      positionId: "position-1",
      runId: "run-1",
      run: { run_id: "run-1" },
      intelItems: [{ title: "Supplier update" }],
      evidences: [{ id: "evidence-1" }],
      thesis: { id: "thesis-1" },
      neighbors: [{ id: "edge-1" }],
      relevancePath: [{ id: "entity-aapl" }, { id: "entity-seed" }],
      overlaps: [{ segment_id: "segment-consumer" }]
    });
    expect(result.current.errors).toEqual({});
  });

  it("keeps successful slices when one request fails", async () => {
    getRunMock.mockResolvedValue(makeRunDetail());
    getNeighborsMock.mockRejectedValue(new Error("neighbors down"));
    getRelevanceMock.mockResolvedValue(makeRelevance());
    getOverlapsMock.mockResolvedValue([makeOverlapGroup()]);

    const { result } = renderHook(() =>
      useStockDetail("entity-aapl", "run-1", "position-1")
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.detail.run?.run_id).toBe("run-1");
    expect(result.current.detail.neighbors).toEqual([]);
    expect(result.current.detail.relevancePath).toHaveLength(2);
    expect(result.current.detail.overlaps).toHaveLength(1);
    expect(result.current.errors.neighbors).toBe("neighbors down");
  });

  it("keeps the detail page available when overlaps fail", async () => {
    getRunMock.mockResolvedValue(makeRunDetail());
    getNeighborsMock.mockResolvedValue({ entity_id: "entity-aapl", edges: [] });
    getRelevanceMock.mockResolvedValue(makeRelevance());
    getOverlapsMock.mockRejectedValue(new Error("overlaps down"));

    const { result } = renderHook(() =>
      useStockDetail("entity-aapl", "run-1", "position-1")
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.detail.run?.run_id).toBe("run-1");
    expect(result.current.detail.overlaps).toEqual([]);
    expect(result.current.errors.overlaps).toBe("overlaps down");
  });
});

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
} {
  let resolveValue: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    resolveValue = resolve;
  });
  return { promise, resolve: resolveValue };
}

function makeRunDetail(): RunDetail {
  return {
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1",
    entity: makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" }),
    evidences: [
      {
        id: "evidence-1",
        source: "web",
        source_tier: 2,
        url: "https://example.com",
        title: "Supplier update",
        snippet: "Supplier pressure eased.",
        captured_at: "2026-06-27T00:00:00Z",
        published_at: null
      }
    ],
    intel_items: [
      {
        title: "Supplier update",
        content: "Supplier pressure eased.",
        event_type: "supply_chain",
        source: "web",
        source_tier: 2,
        url: "https://example.com",
        published_at: null,
        sentiment: { dir: "neutral", conf: 0.7 },
        evidence_ids: ["evidence-1"]
      }
    ],
    thesis: {
      id: "thesis-1",
      summary: "Apple supplier pressure is easing.",
      status: "draft",
      assumptions: [
        {
          text: "Supplier pressure remains observable.",
          kind: "assumption",
          evidence_ids: ["evidence-1"]
        }
      ]
    }
  };
}

function makeEdge(): Edge {
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
    neighbor: makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" })
  };
}

function makeRelevance(): Relevance {
  return {
    entity_id: "entity-aapl",
    position_id: "position-1",
    path: [
      makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" }),
      makeEntity({ id: "entity-seed", name: "Portfolio Seed", symbol: "AAPL" })
    ]
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
