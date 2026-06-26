export type Basis = "inferred" | "source_backed";
export type Relation = "supplier" | "customer" | "competitor" | "belongs_to";
export type NodeType = "company" | "segment" | "theme";
export type PositionKind = "owned" | "watching";
export type RunStatus = "running" | "awaiting_confirmation" | "completed" | "cached" | "failed";

export interface EntityNode {
  id: string;
  name: string;
  node_type: NodeType;
  symbol: string | null;
  market: string | null;
}

export interface Edge {
  id: string;
  to_entity_id: string;
  to_name: string;
  to_symbol: string | null;
  relation: Relation;
  basis: Basis;
  confidence: number;
  evidence_ids: string[];
  source_tier: number | null;
  rationale: string | null;
  neighbor: EntityNode;
}

export interface Evidence {
  id: string;
  source: string;
  source_tier: number;
  url: string | null;
  title: string | null;
  snippet: string;
  captured_at: string;
  published_at: string | null;
}

export interface IntelItem {
  title: string;
  content: string;
  event_type: string;
  source: string;
  source_tier: number;
  url: string | null;
  published_at: string | null;
  sentiment: { dir: "up" | "down" | "neutral"; conf: number };
  evidence_ids: string[];
}

export interface ThesisAssumption {
  text: string;
  kind: "reason" | "assumption" | "risk";
  evidence_ids: string[];
}

export interface Thesis {
  id: string;
  summary: string;
  status: string;
  assumptions: ThesisAssumption[];
}

export interface Position {
  id: string;
  symbol: string;
  market: string;
  name: string | null;
  kind: PositionKind;
  qty?: number | null;
  cost_basis?: number | null;
}

export interface RunDetail {
  run_id: string;
  status: string;
  thesis_id: string | null;
  entity: EntityNode | null;
  evidences: Evidence[];
  intel_items: IntelItem[];
  thesis: Thesis | null;
}

export interface ExpandResult {
  entity_id: string;
  run_id: string;
  status: "completed" | "cached";
  edges: Edge[];
}

export interface Relevance {
  entity_id: string;
  position_id: string;
  path: EntityNode[];
}

export interface CreatePositionInput {
  symbol: string;
  market: string;
  name?: string | null;
  kind?: PositionKind;
  qty?: number | null;
  cost_basis?: number | null;
}

export interface RunSummary {
  run_id: string;
  status: RunStatus;
  thesis_id: string | null;
}

export interface ConfirmationInput {
  status: "confirmed" | "edited" | "rejected";
  edited_summary?: string | null;
  edited_assumptions?: ThesisAssumption[] | null;
}
