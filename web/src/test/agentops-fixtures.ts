import type { AgentOpsRunList, MetricsSummary, RunTrace } from "../types/api";

export function makeAgentOpsRunList(): AgentOpsRunList {
  return { runs: [] };
}

export function makeMetricsSummary(): MetricsSummary {
  return {
    total_runs: 0,
    task_completion_rate: 1,
    avg_latency_ms: 0,
    p95_latency_ms: 0,
    tool_success_rate: 1,
    tool_failure_rate: 0,
    retry_count: 0,
    cache_hit_rate: 0,
    average_token_usage: 0,
    estimated_cost_per_run: 0,
    evidence_coverage: 1,
    unsupported_claim_count: 0,
    rag_retrieval_count: 0
  };
}

export function makeRunTrace(runId = "run-agentops"): RunTrace {
  return {
    run_id: runId,
    status: "completed",
    steps: []
  };
}
