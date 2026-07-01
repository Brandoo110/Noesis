import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import { makeEntity, makePosition } from "../test/m3-fixtures";
import type { Position } from "../types/api";
import { useSupplyChainAnalysis } from "./use-supply-chain-analysis";

vi.mock("../api/client", () => ({
  expandEntity: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("useSupplyChainAnalysis", () => {
  it("expands each researched position seed once and deduplicates repeats", async () => {
    const onAnalyzed = vi.fn();
    expandEntityMock.mockResolvedValue({
      entity_id: "entity-aapl",
      run_id: "run-expand",
      status: "completed",
      edges: []
    });

    const { result } = renderHook(() =>
      useSupplyChainAnalysis({
        activeRun: { entity: null, positionId: null },
        onAnalyzed,
        positions: [
          positionWithSeed("position-aapl", "AAPL", "entity-aapl"),
          positionWithSeed("position-msft", "MSFT", "entity-msft"),
          makePosition({ id: "position-sony", symbol: "SONY" })
        ]
      })
    );

    await act(async () => {
      await result.current.analyze();
    });

    expect(expandEntityMock).toHaveBeenCalledTimes(2);
    expect(expandEntityMock).toHaveBeenNthCalledWith(1, "entity-aapl", "position-aapl");
    expect(expandEntityMock).toHaveBeenNthCalledWith(2, "entity-msft", "position-msft");
    expect(onAnalyzed).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.analyze();
    });

    expect(expandEntityMock).toHaveBeenCalledTimes(2);
    expect(onAnalyzed).toHaveBeenCalledTimes(2);
  });

  it("uses the active run seed before it is persisted on the position row", async () => {
    expandEntityMock.mockResolvedValue({
      entity_id: "entity-sony",
      run_id: "run-expand",
      status: "cached",
      edges: []
    });

    const { result } = renderHook(() =>
      useSupplyChainAnalysis({
        activeRun: {
          entity: makeEntity({ id: "entity-sony", name: "Sony", symbol: "SONY" }),
          positionId: "position-sony"
        },
        positions: [makePosition({ id: "position-sony", symbol: "SONY" })]
      })
    );

    await act(async () => {
      await result.current.analyze();
    });

    expect(expandEntityMock).toHaveBeenCalledWith("entity-sony", "position-sony");
  });
});

function positionWithSeed(
  id: string,
  symbol: string,
  entityId: string
): Position {
  return makePosition({
    id,
    symbol,
    latest_run_entity: makeEntity({ id: entityId, symbol, name: symbol }),
    latest_run_id: `run-${symbol.toLowerCase()}`,
    latest_run_status: "completed"
  });
}
