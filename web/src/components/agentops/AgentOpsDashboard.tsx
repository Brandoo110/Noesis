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
    <section aria-label="AgentOps Dashboard" className="ops-view">
      {error ? (
        <div className="compact-alert" role="alert">
          <span>{error}</span>
          <button
            aria-label="刷新 AgentOps"
            onClick={() => void loadDashboard()}
            type="button"
          >
            刷新
          </button>
        </div>
      ) : null}
      {isLoading ? <p className="empty-note">加载中...</p> : null}

      {metrics ? <MetricsStrip metrics={metrics} /> : null}

      {runs.length > 0 ? (
        <div className="ops-grid">
          <section className="card ops-runs">
            <header className="card-header compact">
              <div>
                <p className="eyebrow">Recent Runs</p>
                <h2>最近 Runs</h2>
              </div>
              <button
                aria-label="刷新 AgentOps"
                className="secondary-button small"
                onClick={() => void loadDashboard()}
                type="button"
              >
                刷新
              </button>
            </header>
            <ul aria-label="AgentOps run list">
              {runs.map((run) => (
                <li key={run.run_id}>
                  <button
                    aria-pressed={run.run_id === selectedRunId}
                    className="run-card"
                    onClick={() => setSelectedRunId(run.run_id)}
                    type="button"
                  >
                    <strong>{run.run_id}</strong>
                    <span>{run.status}</span>
                    <small>{formatMs(run.latency_ms)} · {run.tool_count} tools</small>
                    <small>cache {formatPercent(run.cache_hit_rate)}</small>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section aria-label="Run trace timeline" className="card run-trace">
            <header className="trace-header">
              <div>
                <p className="eyebrow">Run Trace</p>
                <h2>Run Trace</h2>
              </div>
              {selectedRun ? <span>{selectedRun.status}</span> : null}
            </header>
            {isTraceLoading ? <p className="empty-note">加载中...</p> : null}
            {trace ? (
              <ol>
                {trace.steps.map((step, index) => (
                  <TraceStep
                    hasLine={index < trace.steps.length - 1}
                    key={`${step.kind}-${step.name}-${index}`}
                    step={step}
                  />
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
    <div aria-label="AgentOps 指标" className="ops-metrics">
      {items.map(([label, value]) => (
        <article key={label}>
          <strong>{value}</strong>
          <span>{label}</span>
        </article>
      ))}
    </div>
  );
}

function TraceStep({
  hasLine,
  step
}: {
  hasLine: boolean;
  step: RunTraceStep;
}): JSX.Element {
  return (
    <li className={`trace-step ${step.status}`}>
      <i />
      {hasLine ? <b aria-hidden="true" /> : null}
      <div>
        <header>
          <strong>{step.name}</strong>
          <span>{step.kind}</span>
          <em>{step.status}</em>
          <small>{formatMs(step.latency_ms)}</small>
        </header>
        <p>
          {step.input_summary ? <small>{step.input_summary}</small> : null}
          {step.output_summary ? <small>{step.output_summary}</small> : null}
          {step.cache_hit !== null ? (
            <small>{step.cache_hit ? "cache hit" : "cache miss"}</small>
          ) : null}
          {step.retry_count !== null ? <small>{`retry ${step.retry_count}`}</small> : null}
        </p>
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
