import { makeOverlapGroup, makeRunHealth } from "../../test/m3-fixtures";
import type { PortfolioBrief, Position, RunDetail } from "../../types/api";

export function makePosition(overrides: Partial<Position> = {}): Position {
  return {
    id: "position-1",
    symbol: "AAPL",
    market: "US",
    name: "Apple",
    kind: "owned",
    qty: null,
    cost_basis: null,
    ...overrides
  };
}

export function makeRunDetail(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1",
    entity: {
      id: "entity-aapl",
      name: "Apple Inc.",
      node_type: "company",
      symbol: "AAPL",
      market: "US"
    },
    evidences: [],
    intel_items: [],
    thesis: null,
    ...overrides
  };
}

export function makeBrief(): PortfolioBrief {
  return {
    generated_at: "2026-06-28T00:00:00Z",
    positions: [
      {
        position_id: "position-1",
        symbol: "AAPL",
        name: "Apple",
        thesis_summary: "Apple supplier pressure is easing.",
        thesis_status: "confirmed"
      }
    ],
    overlaps: [makeOverlapGroup()],
    run_health: makeRunHealth({ total_latest_runs: 1, completed: 1 })
  };
}
