export interface AgentOpsRunSummary {
  run_id: string;
  position_id: string | null;
  entity_id: string | null;
  node_kind: string;
  target_name: string | null;
  target_symbol: string | null;
  target_market: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
  evidence_count: number;
  tool_count: number;
  cache_hit_rate: number;
  diagnostic_tags: string[];
  last_step_name: string | null;
  slowest_step_name: string | null;
  slowest_step_latency_ms: number | null;
  has_degraded_step: boolean;
  has_failed_step: boolean;
  has_pending_confirmation: boolean;
}

export interface AgentOpsRunList {
  runs: AgentOpsRunSummary[];
}

export interface ClearRunsResult {
  deleted: Record<string, number>;
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
  error_kind: string | null;
  error_code: string | null;
  error_message: string | null;
  http_status: number | null;
  provider: string | null;
  model_id: string | null;
  token_input: number | null;
  token_output: number | null;
  estimated_cost_usd: number | null;
  cache_key: string | null;
  fallback_used: string | null;
  degraded_reason: string | null;
}

export interface RunDiagnostic {
  severity: "ok" | "info" | "warning" | "critical";
  title: string;
  summary: string;
  tags: string[];
  slowest_step_name: string | null;
  slowest_step_latency_ms: number | null;
  next_actions: string[];
}

export interface EvidencePreview {
  evidence_id: string;
  title: string | null;
  source: string;
  url: string | null;
  snippet: string;
  source_tier: number | null;
  published_at: string | null;
}

export interface RunTrace {
  run_id: string;
  status: string;
  diagnostic: RunDiagnostic;
  steps: RunTraceStep[];
  evidence_previews: EvidencePreview[];
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
  cost_tracking_enabled: boolean;
  evidence_coverage: number;
  unsupported_claim_count: number;
  rag_retrieval_count: number;
}
