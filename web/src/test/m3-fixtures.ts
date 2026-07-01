import type {
  Edge,
  EntityNode,
  Evidence,
  ExpandResult,
  OverlapGroup,
  Position,
  PortfolioRunHealth,
  RunDetail
} from "../types/api";

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

export function makeEntity(overrides: Partial<EntityNode> = {}): EntityNode {
  return {
    id: "entity-aapl",
    name: "Apple Inc.",
    node_type: "company",
    symbol: "AAPL",
    market: "US",
    ...overrides
  };
}

export function makeEvidence(): Evidence {
  return {
    id: "evidence-1",
    source: "web",
    source_tier: 2,
    url: "https://example.com/evidence-1",
    title: "Supplier evidence",
    snippet: "Supplier pressure eased.",
    captured_at: "2026-06-27T00:00:00Z",
    published_at: null
  };
}

export function makeEdge(
  id: string,
  neighbor: EntityNode,
  basis: Edge["basis"],
  evidenceIds: string[]
): Edge {
  return {
    id,
    to_entity_id: neighbor.id,
    to_name: neighbor.name,
    to_symbol: neighbor.symbol,
    relation: basis === "source_backed" ? "supplier" : "belongs_to",
    basis,
    confidence: basis === "source_backed" ? 0.82 : 0.54,
    evidence_ids: evidenceIds,
    source_tier: basis === "source_backed" ? 2 : null,
    rationale: `${neighbor.name} relation`,
    neighbor
  };
}

export function makeExpandResult(edges: Edge[]): ExpandResult {
  return {
    entity_id: "entity-aapl",
    run_id: "run-expand-1",
    status: "completed",
    edges
  };
}

export function makeOverlapGroup(
  overrides: Partial<OverlapGroup> = {}
): OverlapGroup {
  return {
    segment_id: "segment-consumer",
    segment_name: "Consumer Electronics",
    node_type: "segment",
    basis: "inferred",
    positions: [
      {
        position_id: "position-1",
        symbol: "AAPL",
        entity_id: "entity-aapl",
        confidence: 0.9
      },
      {
        position_id: "position-msft",
        symbol: "MSFT",
        entity_id: "entity-msft",
        confidence: 0.7
      }
    ],
    ...overrides
  };
}

export function makeRunHealth(
  overrides: Partial<PortfolioRunHealth> = {}
): PortfolioRunHealth {
  return {
    total_latest_runs: 0,
    running: 0,
    awaiting_confirmation: 0,
    completed: 0,
    failed: 0,
    completed_without_thesis: 0,
    degraded_runs: 0,
    failed_runs: [],
    degraded_reasons: [],
    ...overrides
  };
}

export function makeRunDetail(
  entity: EntityNode,
  evidence: Evidence
): RunDetail {
  return {
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1",
    entity,
    evidences: [evidence],
    intel_items: [
      {
        title: "Supplier update",
        content: "Supplier pressure eased.",
        event_type: "supply_chain",
        source: "web",
        source_tier: 2,
        url: evidence.url,
        published_at: null,
        sentiment: { dir: "neutral", conf: 0.7 },
        evidence_ids: [evidence.id]
      }
    ],
    thesis: {
      id: "thesis-1",
      summary: "Apple supplier pressure is easing.",
      status: "draft",
      assumptions: [
        {
          text: "Supplier conditions support the current thesis.",
          kind: "reason",
          evidence_ids: [evidence.id]
        },
        {
          text: "Supplier conditions remain observable.",
          kind: "assumption",
          evidence_ids: [evidence.id]
        },
        {
          text: "Supplier conditions could reverse.",
          kind: "risk",
          evidence_ids: [evidence.id]
        }
      ]
    }
  };
}
