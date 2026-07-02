import { useCallback, useEffect, useMemo, useState } from "react";

import { getMetricsSummary, getRunTrace, listRuns } from "../../api/client";
import type {
  AgentOpsRunSummary,
  MetricsSummary,
  RunTrace,
  RunTraceStep
} from "../../types/api";

export function AgentOpsDashboard(): JSX.Element {
  const [runs, setRuns] = useState<AgentOpsRunSummary[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [trace, setTrace] = useState<RunTrace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTraceLoading, setIsTraceLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedRun = useMemo(
    () => runs.find((item) => item.run_id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );

  const loadDashboard = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [runList, summary] = await Promise.all([
        listRuns(),
        getMetricsSummary()
      ]);
      setRuns(runList.runs);
      setMetrics(summary);
      setSelectedRunId((current) => current ?? runList.runs[0]?.run_id ?? null);
    } catch (caught) {
      setError(toErrorMessage(caught));
      setRuns([]);
      setMetrics(null);
      setTrace(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (selectedRunId === null) {
      setTrace(null);
      return;
    }
    let isCurrent = true;
    setIsTraceLoading(true);
    getRunTrace(selectedRunId)
      .then((payload) => {
        if (isCurrent) {
          setTrace(payload);
        }
      })
      .catch((caught) => {
        if (isCurrent) {
          setError(toErrorMessage(caught));
          setTrace(null);
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsTraceLoading(false);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [selectedRunId]);

  return (
    <section aria-label="AgentOps Dashboard" className="surface agentops-surface">
      <header className="section-heading">
        <div>
          <p className="eyebrow">AgentOps</p>
          <h2>Run Operations</h2>
        </div>
        <button
          aria-label="刷新 AgentOps"
          onClick={() => void loadDashboard()}
          type="button"
        >
          Refresh
        </button>
      </header>

      {error ? <p className="alert compact-alert" role="alert">{error}</p> : null}
      {isLoading ? <p className="muted">加载中...</p> : null}

      {metrics ? <MetricsStrip metrics={metrics} /> : null}

      {runs.length > 0 ? (
        <div className="agentops-body">
          <ul aria-label="AgentOps run list" className="agentops-run-list">
            {runs.map((run) => (
              <li key={run.run_id}>
                <button
                  aria-pressed={run.run_id === selectedRunId}
                  onClick={() => setSelectedRunId(run.run_id)}
                  type="button"
                >
                  <span>{run.run_id}</span>
                  <small>{run.status}</small>
                  <small>{formatMs(run.latency_ms)} · {run.tool_count} tools</small>
                  <small>cache {formatPercent(run.cache_hit_rate)}</small>
                </button>
              </li>
            ))}
          </ul>

          <section aria-label="Run trace timeline" className="agentops-timeline">
            <h3>{selectedRun?.run_id ?? "Run trace"}</h3>
            {isTraceLoading ? <p className="muted">加载中...</p> : null}
            {trace ? (
              <ol>
                {trace.steps.map((step, index) => (
                  <TraceStep key={`${step.kind}-${step.name}-${index}`} step={step} />
                ))}
              </ol>
            ) : null}
          </section>
        </div>
      ) : !isLoading && !error ? (
        <p className="empty-note">No runs yet</p>
      ) : null}
    </section>
  );
}

function MetricsStrip({ metrics }: { metrics: MetricsSummary }): JSX.Element {
  const items = [
    ["runs", String(metrics.total_runs)],
    ["complete", formatPercent(metrics.task_completion_rate)],
    ["avg latency", formatMs(metrics.avg_latency_ms)],
    ["P95 latency", formatMs(metrics.p95_latency_ms)],
    ["tool success", formatPercent(metrics.tool_success_rate)],
    ["tool failure", formatPercent(metrics.tool_failure_rate)],
    ["retry count", String(metrics.retry_count)],
    ["cache hit", formatPercent(metrics.cache_hit_rate)],
    ["tokens/run", String(metrics.average_token_usage)],
    ["cost/run", formatUsd(metrics.estimated_cost_per_run)],
    ["evidence coverage", formatPercent(metrics.evidence_coverage)],
    ["unsupported", String(metrics.unsupported_claim_count)],
    ["RAG retrievals", String(metrics.rag_retrieval_count)]
  ];

  return (
    <div aria-label="AgentOps 指标" className="agentops-metrics">
      {items.map(([label, value]) => (
        <span key={label}>
          <strong>{value}</strong>
          <small>{label}</small>
        </span>
      ))}
    </div>
  );
}

function TraceStep({ step }: { step: RunTraceStep }): JSX.Element {
  return (
    <li>
      <div>
        <strong>{step.name}</strong>
        <span>{step.kind}</span>
      </div>
      <p>{step.status} · {formatMs(step.latency_ms)}</p>
      <div className="agentops-step-meta">
        {step.cache_hit !== null ? (
          <small>{step.cache_hit ? "cache hit" : "cache miss"}</small>
        ) : null}
        {step.retry_count !== null ? <small>{`retry ${step.retry_count}`}</small> : null}
        {step.input_summary ? <small>{step.input_summary}</small> : null}
        {step.output_summary ? <small>{step.output_summary}</small> : null}
      </div>
      {step.evidence_ids.length > 0 ? (
        <small>{step.evidence_ids.join(", ")}</small>
      ) : null}
    </li>
  );
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatMs(value: number | null): string {
  if (value === null) {
    return "pending";
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }
  return `${value}ms`;
}

function formatUsd(value: number): string {
  return `$${value.toFixed(6)}`;
}

function toErrorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message;
  }
  return "unknown error";
}
