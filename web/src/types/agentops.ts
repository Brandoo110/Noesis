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
