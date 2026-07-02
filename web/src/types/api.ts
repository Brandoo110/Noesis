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
  latest_run_id?: string | null;
  latest_run_status?: RunStatus | string | null;
  latest_run_entity?: EntityNode | null;
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

export interface OverlapPosition {
  position_id: string;
  symbol: string;
  entity_id: string;
  confidence: number;
}

export interface OverlapGroup {
  segment_id: string;
  segment_name: string;
  node_type: "segment" | "theme";
  basis: Basis;
  positions: OverlapPosition[];
}

export interface SharedPosition {
  position_id: string;
  symbol: string | null;
  entity_id: string;
  confidence: number;
}

export interface SharedSupplierGroup {
  supplier_id: string;
  supplier_name: string;
  node_type: "company";
  basis: Basis;
  positions: SharedPosition[];
}

export interface MatrixAxis {
  position_id: string;
  symbol: string | null;
  label: string;
}

export interface CorrelationCell {
  a_position_id: string;
  b_position_id: string;
  shared_count: number;
  shared_suppliers: string[];
}

export interface CorrelationMatrix {
  positions: MatrixAxis[];
  cells: CorrelationCell[];
}

export interface BriefPosition {
  position_id: string;
  symbol: string;
  name: string | null;
  thesis_summary: string | null;
  thesis_status: string | null;
}

export interface FailedRun {
  position_id: string;
  symbol: string;
  run_id: string;
  status: string;
  reason: string | null;
}

export interface DegradedReason {
  reason: string;
  count: number;
}

export interface PortfolioRunHealth {
  total_latest_runs: number;
  running: number;
  awaiting_confirmation: number;
  completed: number;
  failed: number;
  completed_without_thesis: number;
  degraded_runs: number;
  failed_runs: FailedRun[];
  degraded_reasons: DegradedReason[];
}

export interface PortfolioBrief {
  generated_at: string;
  positions: BriefPosition[];
  overlaps: OverlapGroup[];
  run_health: PortfolioRunHealth;
}

export interface CreatePositionInput {
  symbol?: string | null;
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

export interface AgentOpsRunSummary {
  run_id: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
  evidence_count: number;
  tool_count: number;
  cache_hit_rate: number;
}

export interface AgentOpsRunList {
  runs: AgentOpsRunSummary[];
}

export interface RunTraceStep {
  kind: "node" | "tool";
  name: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
  input_summary: string | null;
  output_summary: string | null;
  cache_hit: boolean | null;
  retry_count: number | null;
  evidence_ids: string[];
}

export interface RunTrace {
  run_id: string;
  status: string;
  steps: RunTraceStep[];
}

export interface MetricsSummary {
  total_runs: number;
  task_completion_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  tool_success_rate: number;
  tool_failure_rate: number;
  retry_count: number;
  cache_hit_rate: number;
  average_token_usage: number;
  estimated_cost_per_run: number;
  evidence_coverage: number;
  unsupported_claim_count: number;
  rag_retrieval_count: number;
}

export interface ConfirmationInput {
  status: "confirmed" | "edited" | "rejected";
  edited_summary?: string | null;
  edited_assumptions?: ThesisAssumption[] | null;
}
