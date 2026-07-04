import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { clearRuns, getMetricsSummary, getRunTrace, listRuns } from "../../api/client";
import type {
  AgentOpsRunSummary,
  EvidencePreview,
  MetricsSummary,
  RunTrace,
  RunTraceStep
} from "../../types/api";

const RUNS_PER_PAGE = 8;
const DASHBOARD_REFRESH_MS = 10_000;
type TraceFilter = "all" | "issues" | "tools" | "slow" | "evidence";
type LoadDashboardOptions = { silent?: boolean };

const TRACE_FILTERS: Array<{ id: TraceFilter; label: string }> = [
  { id: "all", label: "全部" },
  { id: "issues", label: "问题" },
  { id: "tools", label: "工具" },
  { id: "slow", label: "慢步骤" },
  { id: "evidence", label: "证据" }
];

export function AgentOpsDashboard(): JSX.Element {
  const runPanelsRef = useRef<HTMLDivElement | null>(null);
  const [runs, setRuns] = useState<AgentOpsRunSummary[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [trace, setTrace] = useState<RunTrace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTraceLoading, setIsTraceLoading] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [traceFilter, setTraceFilter] = useState<TraceFilter>("all");
  const [expandedStepKey, setExpandedStepKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedRun = useMemo(
    () => runs.find((item) => item.run_id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );
  const totalPages = Math.max(1, Math.ceil(runs.length / RUNS_PER_PAGE));
  const pageStart = currentPage * RUNS_PER_PAGE;
  const pageRuns = runs.slice(pageStart, pageStart + RUNS_PER_PAGE);
  const slowThreshold = useMemo(
    () => (trace ? traceSlowThreshold(trace.steps) : 30_000),
    [trace]
  );
  const filteredSteps = useMemo(
    () => (trace ? filterTraceSteps(trace.steps, traceFilter, slowThreshold) : []),
    [slowThreshold, trace, traceFilter]
  );

  const loadDashboard = useCallback(
    async (options: LoadDashboardOptions = {}): Promise<void> => {
    if (!options.silent) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const [runList, summary] = await Promise.all([
        listRuns(),
        getMetricsSummary()
      ]);
      setRuns(runList.runs);
      setMetrics(summary);
      setSelectedRunId((current) => current ?? runList.runs[0]?.run_id ?? null);
      setCurrentPage((current) =>
        Math.min(current, Math.max(0, Math.ceil(runList.runs.length / RUNS_PER_PAGE) - 1))
      );
    } catch (caught) {
      setError(toErrorMessage(caught));
      if (!options.silent) {
        setRuns([]);
        setMetrics(null);
        setTrace(null);
        setSelectedRunId(null);
        setCurrentPage(0);
      }
    } finally {
      if (!options.silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void loadDashboard({ silent: true });
    }, DASHBOARD_REFRESH_MS);
    return () => window.clearInterval(intervalId);
  }, [loadDashboard]);

  useEffect(() => {
    if (runs.length === 0) {
      setSelectedRunId(null);
      setCurrentPage(0);
      return;
    }
    if (!runs.some((run) => run.run_id === selectedRunId)) {
      setSelectedRunId(runs[0].run_id);
    }
  }, [runs, selectedRunId]);

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

  function goToPage(nextPage: number): void {
    const bounded = Math.max(0, Math.min(nextPage, totalPages - 1));
    setCurrentPage(bounded);
    setSelectedRunId(runs[bounded * RUNS_PER_PAGE]?.run_id ?? null);
  }

  function selectRun(runId: string): void {
    setSelectedRunId(runId);
    scrollToRunPanels(runPanelsRef.current);
  }

  async function handleClearRuns(): Promise<void> {
    if (!window.confirm("清空所有 run 历史和派生结果？持仓与实体会保留。")) {
      return;
    }
    setIsClearing(true);
    setError(null);
    try {
      await clearRuns();
      setRuns([]);
      setMetrics(null);
      setSelectedRunId(null);
      setTrace(null);
      setCurrentPage(0);
      await loadDashboard();
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsClearing(false);
    }
  }

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
      {trace ? <RunDiagnosticPanel trace={trace} /> : null}

      {runs.length > 0 ? (
        <div aria-label="AgentOps run panels" className="ops-grid" ref={runPanelsRef}>
          <section className="card ops-runs">
            <header className="card-header compact">
              <div>
                <p className="eyebrow">Recent Runs</p>
                <h2>最近 Runs</h2>
              </div>
              <div className="ops-run-actions">
                <button
                  aria-label="清空 Run 记录"
                  className="danger-button small"
                  disabled={isClearing}
                  onClick={() => void handleClearRuns()}
                  type="button"
                >
                  清空
                </button>
                <button
                  aria-label="刷新 AgentOps"
                  className="secondary-button small"
                  onClick={() => void loadDashboard()}
                  type="button"
                >
                  刷新
                </button>
              </div>
            </header>
            <ul aria-label="AgentOps run list">
              {pageRuns.map((run) => (
                <li key={run.run_id}>
                  <button
                    aria-pressed={run.run_id === selectedRunId}
                    className="run-card"
                    onClick={() => selectRun(run.run_id)}
                    type="button"
                  >
                    <strong className="run-target-title">{runTargetTitle(run)}</strong>
                    <small className="run-target-meta">{runTargetMeta(run)}</small>
                    <span>{run.status}</span>
                    <small>{formatMs(run.latency_ms)} · {run.tool_count} tools</small>
                    <small>cache {formatPercent(run.cache_hit_rate)}</small>
                    <small className="run-id">{shortRunId(run.run_id)}</small>
                    {(run.diagnostic_tags ?? []).length > 0 ? (
                      <span className="run-tags">
                        {(run.diagnostic_tags ?? []).slice(0, 3).map((tag) => (
                          <em key={tag}>{runTagLabel(tag)}</em>
                        ))}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
            <footer className="ops-pagination" aria-label="Run pagination">
              <span>
                {pageStart + 1}-{Math.min(pageStart + RUNS_PER_PAGE, runs.length)} / {runs.length}
              </span>
              <div>
                <button
                  className="secondary-button small"
                  disabled={currentPage === 0}
                  onClick={() => goToPage(currentPage - 1)}
                  type="button"
                >
                  上一页
                </button>
                <button
                  className="secondary-button small"
                  disabled={currentPage >= totalPages - 1}
                  onClick={() => goToPage(currentPage + 1)}
                  type="button"
                >
                  下一页
                </button>
              </div>
            </footer>
          </section>

          <section aria-label="Run trace timeline" className="card run-trace">
            <header className="trace-header">
              <div>
                <p className="eyebrow">Run Trace</p>
                <h2>Run Trace</h2>
              </div>
              {selectedRun ? <span>{selectedRun.status}</span> : null}
            </header>
            {trace ? (
              <div aria-label="Trace filters" className="trace-filters">
                {TRACE_FILTERS.map((item) => (
                  <button
                    aria-pressed={traceFilter === item.id}
                    key={item.id}
                    onClick={() => setTraceFilter(item.id)}
                    type="button"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            ) : null}
            {isTraceLoading ? <p className="empty-note">加载中...</p> : null}
            {trace ? (
              filteredSteps.length > 0 ? (
                <ol>
                  {filteredSteps.map((step, index) => (
                  <TraceStep
                    costCurrency={metrics?.cost_currency ?? "CNY"}
                    evidencePreviews={trace.evidence_previews ?? []}
                    expanded={expandedStepKey === stepKey(step, index)}
                    hasLine={index < filteredSteps.length - 1}
                    key={stepKey(step, index)}
                    maxLatency={slowThreshold}
                    onToggle={() =>
                      setExpandedStepKey((current) =>
                        current === stepKey(step, index) ? null : stepKey(step, index)
                      )
                    }
                    step={step}
                  />
                  ))}
                </ol>
              ) : (
                <p className="empty-note">没有匹配的 trace step</p>
              )
            ) : null}
          </section>
        </div>
      ) : !isLoading && !error ? (
        <p className="empty-note">No runs yet</p>
      ) : null}

      <AgentOpsGuide />
    </section>
  );
}

function RunDiagnosticPanel({ trace }: { trace: RunTrace }): JSX.Element {
  const diagnostic = trace.diagnostic ?? fallbackDiagnostic();
  return (
    <section
      aria-label="Run diagnostic summary"
      className={`card run-diagnostic ${diagnostic.severity}`}
    >
      <div>
        <p className="eyebrow">Run Diagnostics</p>
        <h2>{diagnostic.title}</h2>
        <p>{diagnostic.summary}</p>
      </div>
      <div className="diagnostic-meta">
        {diagnostic.tags.length > 0 ? (
          <span className="run-tags">
            {diagnostic.tags.map((tag) => (
              <em key={tag}>{runTagLabel(tag)}</em>
            ))}
          </span>
        ) : null}
        {diagnostic.slowest_step_name ? (
          <small>
            最慢步骤：{diagnostic.slowest_step_name} ·{" "}
            {formatMs(diagnostic.slowest_step_latency_ms)}
          </small>
        ) : null}
        <ul>
          {diagnostic.next_actions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function scrollToRunPanels(element: HTMLElement | null): void {
  if (!element) {
    return;
  }
  const topbar = document.querySelector<HTMLElement>(".topbar");
  const topbarHeight = topbar?.getBoundingClientRect().height ?? 0;
  const targetTop = window.scrollY + element.getBoundingClientRect().top - topbarHeight - 16;
  window.scrollTo({ behavior: "smooth", top: Math.max(0, targetTop) });
}

function MetricsStrip({ metrics }: { metrics: MetricsSummary }): JSX.Element {
  const costValue = metrics.cost_tracking_enabled
    ? formatMoney(metrics.estimated_cost_per_run, metrics.cost_currency)
    : "未配置单价";
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
    ["cost/run", costValue],
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
  costCurrency,
  evidencePreviews,
  expanded,
  hasLine,
  maxLatency,
  onToggle,
  step
}: {
  costCurrency: string;
  evidencePreviews: EvidencePreview[];
  expanded: boolean;
  hasLine: boolean;
  maxLatency: number;
  onToggle: () => void;
  step: RunTraceStep;
}): JSX.Element {
  const previews = evidencePreviews.filter((item) =>
    step.evidence_ids.includes(item.evidence_id)
  );
  const barWidth = step.latency_ms === null
    ? 0
    : Math.min(100, Math.max(4, (step.latency_ms / Math.max(maxLatency, 1)) * 100));
  return (
    <li className={traceStepClassName(step)}>
      <i />
      {hasLine ? <b aria-hidden="true" /> : null}
      <div>
        <button
          aria-expanded={expanded}
          aria-label={`${expanded ? "收起" : "展开"} ${step.name}`}
          className="trace-step-toggle"
          onClick={onToggle}
          type="button"
        >
          <header>
            <strong>{step.name}</strong>
            <span>{step.kind}</span>
            <em>{step.status}</em>
            <small>{formatMs(step.latency_ms)}</small>
            {step.status === "degraded" ? <small>降级</small> : null}
            {step.error_message ? <small>错误</small> : null}
          </header>
          <span className="latency-bar">
            <span style={{ width: `${barWidth}%` }} />
          </span>
        </button>
        <p>
          {step.input_summary ? <small>{step.input_summary}</small> : null}
          {step.output_summary ? <small>{step.output_summary}</small> : null}
          {step.cache_hit !== null ? (
            <small>{step.cache_hit ? "cache hit" : "cache miss"}</small>
          ) : null}
          {step.retry_count !== null ? <small>{`retry ${step.retry_count}`}</small> : null}
          {step.evidence_ids.length > 0 ? (
            <small>{`${step.evidence_ids.length} evidence`}</small>
          ) : null}
        </p>
        {expanded ? (
          <TraceStepDetail costCurrency={costCurrency} previews={previews} step={step} />
        ) : null}
      </div>
      {step.evidence_ids.length > 0 ? (
        <small>{step.evidence_ids.join(", ")}</small>
      ) : null}
    </li>
  );
}

function TraceStepDetail({
  costCurrency,
  previews,
  step
}: {
  costCurrency: string;
  previews: EvidencePreview[];
  step: RunTraceStep;
}): JSX.Element {
  return (
    <section aria-label={`${step.name} step detail`} className="trace-step-detail">
      {step.input_summary ? <DetailBlock label="Input" value={step.input_summary} /> : null}
      {step.output_summary ? (
        <DetailBlock label="Output" value={step.output_summary} />
      ) : null}
      {step.error_message ? (
        <DetailBlock
          label="Error"
          value={`${step.error_kind ?? "unknown"} · ${step.error_message}`}
        />
      ) : null}
      {step.degraded_reason || step.fallback_used ? (
        <DetailBlock
          label="Degrade"
          value={`${step.degraded_reason ?? "未记录具体原因"} · ${
            step.fallback_used ?? "未记录 fallback"
          }`}
        />
      ) : null}
      {step.kind === "tool" ? (
        <ToolDetail costCurrency={costCurrency} step={step} />
      ) : null}
      {step.evidence_ids.length > 0 ? (
        <EvidenceDetail ids={step.evidence_ids} previews={previews} />
      ) : null}
    </section>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <article>
      <strong>{label}</strong>
      <p>{value}</p>
    </article>
  );
}

function ToolDetail({
  costCurrency,
  step
}: {
  costCurrency: string;
  step: RunTraceStep;
}): JSX.Element {
  const details = [
    step.provider ? `provider ${step.provider}` : null,
    step.model_id ? `model ${step.model_id}` : null,
    step.cache_key ? `cache ${step.cache_key}` : null,
    step.retry_count !== null ? `retry ${step.retry_count}` : null,
    step.token_input !== null || step.token_output !== null
      ? `tokens ${step.token_input ?? 0}/${step.token_output ?? 0}`
      : null,
    step.estimated_cost_usd !== null
      ? `cost ${formatMoney(step.estimated_cost_usd, costCurrency)}`
      : null
  ].filter((item): item is string => item !== null);
  return <DetailBlock label="Tool / Cache" value={details.join(" · ") || "未记录"} />;
}

function EvidenceDetail({
  ids,
  previews
}: {
  ids: string[];
  previews: EvidencePreview[];
}): JSX.Element {
  return (
    <article>
      <strong>Evidence</strong>
      {previews.length > 0 ? (
        <ul className="evidence-preview-list">
          {previews.map((item) => (
            <li key={item.evidence_id}>
              <b>{item.title ?? item.evidence_id}</b>
              <span>{item.source} · tier {item.source_tier ?? "n/a"}</span>
              <p>{item.snippet}</p>
              {item.url ? (
                <a href={item.url} rel="noreferrer" target="_blank">
                  查看来源
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p>{ids.join(", ")} · 未找到预览</p>
      )}
    </article>
  );
}

function AgentOpsGuide(): JSX.Element {
  const items = [
    {
      term: "Run Diagnostics",
      body: "先看这块。它会把当前选中 run 的结论提前说清楚：是否在等确认、是否失败、是否降级、是否低证据、是否有明显慢步骤。这里如果已经指出问题，优先按右侧 next actions 去看对应 trace。"
    },
    {
      term: "Metrics",
      body: "顶部数字看长期健康度，不是看单条 run。完成率低说明流程经常没跑完；平均耗时或 P95 很高说明有慢节点；证据覆盖率低说明结论可能缺证据；tool failure 高说明外部工具或模型调用不稳。"
    },
    {
      term: "Run",
      body: "一次 Agent 执行。每发起一次研究，或系统触发一次分析，都会生成一条 run。左侧卡片先看公司 / symbol / market，确认自己点的是哪一个标的，再看 status 和标签。"
    },
    {
      term: "Status",
      body: "看这条 run 停在哪。completed 表示已跑完；running 表示还在处理中；如果是 awaiting_confirmation，说明研究已经生成待确认内容，需要去确认或编辑研究假设；failed 表示中途失败，要看 trace 里的失败 step。"
    },
    {
      term: "Latency",
      body: "看时间是不是异常。pending 代表还没有最终耗时；如果单条 run 很慢，先看 Run Diagnostics 标出的最慢步骤，再切到「慢步骤」筛选确认是不是 LLM、搜索、读取或 finalize 卡住。"
    },
    {
      term: "Tools",
      body: "看 Agent 有没有真的动用外部能力，比如搜索、网页读取、LLM 生成、PDF 解析或缓存查询。工具数太少但 run 却 completed 时，要展开 trace 看是否走了降级或缓存。"
    },
    {
      term: "Cache",
      body: "看这次是不是复用了旧结果。cache hit 多说明成本低、速度快，但如果你刚改了输入却仍大量命中缓存，要确认是否拿到的是旧证据；cache miss 多说明这次重新检索或生成。"
    },
    {
      term: "Run Trace",
      body: "执行时间线。它按顺序告诉你 Agent 先做了什么、后做了什么、每一步成功、降级、失败还是等待。排障时不要只看最后状态，要沿 trace 找第一个异常 step。"
    },
    {
      term: "Trace filters",
      body: "先用筛选缩小范围。点「问题」只看 failed / degraded / retry；点「工具」看外部调用；点「慢步骤」找耗时瓶颈；点「证据」只看挂了 evidence 的步骤。"
    },
    {
      term: "Node / Tool",
      body: "Node 是 Agent 自己的业务步骤，比如解析输入、构建证据、生成研究假设、风险检查。Tool 是 node 调用的外部能力，比如 search、reader、llm。Tool 失败通常是网络、供应商或 key；Node 降级通常是业务兜底生效。"
    },
    {
      term: "Input / Output",
      body: "展开 step 后先看 Input / Output。Input 看这一步吃进去的对象、query、证据或状态是否正确；Output 看它产出了什么。如果 Input 已经错了，问题在上游；如果 Input 对但 Output 错，问题在这个 step 或它调用的 tool。"
    },
    {
      term: "Evidence",
      body: "看结论有没有证据支撑。Evidence preview 会显示标题、来源、tier、片段和链接。证据为空、tier 低或片段和结论对不上，就不要先信结论，应该回到 ingest / evidence_build / intel_synth 这些步骤继续看。"
    },
    {
      term: "Retry / Failed",
      body: "retry 表示这一步重试过，可能遇到超时、限流或临时失败；failed 表示没有恢复。重试多但最终成功，说明链路能自愈但可能慢；failed 或 degraded 要展开看 Error、Degrade、Tool / Cache。"
    }
  ];

  return (
    <section aria-label="AgentOps 解读指南" className="card ops-guide">
      <header className="card-header compact">
        <div>
          <p className="eyebrow">How to read AgentOps</p>
          <h2>怎么读上面的信息</h2>
        </div>
      </header>
      <p className="ops-guide-intro">
        可以按这个顺序读：先看 Run Diagnostics 判断这次 run 的结论，再看左侧
        Recent Runs 确认调研对象，最后用 Run Trace 的筛选和 step 展开定位具体原因。
      </p>
      <dl className="ops-guide-list">
        {items.map((item) => (
          <div key={item.term}>
            <dt>{item.term}</dt>
            <dd>{item.body}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function filterTraceSteps(
  steps: RunTraceStep[],
  filter: TraceFilter,
  slowThreshold: number
): RunTraceStep[] {
  if (filter === "issues") {
    return steps.filter(isIssueStep);
  }
  if (filter === "tools") {
    return steps.filter((step) => step.kind === "tool");
  }
  if (filter === "slow") {
    return steps.filter(
      (step) => step.latency_ms !== null && step.latency_ms >= slowThreshold
    );
  }
  if (filter === "evidence") {
    return steps.filter((step) => step.evidence_ids.length > 0);
  }
  return steps;
}

function traceSlowThreshold(steps: RunTraceStep[]): number {
  const latencies = steps
    .map((step) => step.latency_ms)
    .filter((value): value is number => value !== null)
    .sort((left, right) => left - right);
  if (latencies.length === 0) {
    return 30_000;
  }
  const index = Math.max(0, Math.ceil(latencies.length * 0.9) - 1);
  return Math.max(30_000, latencies[index]);
}

function isIssueStep(step: RunTraceStep): boolean {
  return step.status === "failed" || step.status === "degraded" ||
    (step.retry_count ?? 0) > 0;
}

function traceStepClassName(step: RunTraceStep): string {
  const classes = ["trace-step", step.status];
  if (isIssueStep(step)) {
    classes.push("issue");
  }
  return classes.join(" ");
}

function stepKey(step: RunTraceStep, index: number): string {
  return `${step.kind}-${step.name}-${step.started_at}-${index}`;
}

function runTagLabel(tag: string): string {
  const labels: Record<string, string> = {
    waiting_confirmation: "等确认",
    slow: "慢",
    low_evidence: "低证据",
    degraded: "降级",
    failed: "失败",
    no_tools: "无工具"
  };
  return labels[tag] ?? tag;
}

function runTargetTitle(run: AgentOpsRunSummary): string {
  return run.target_name ?? run.target_symbol ?? run.entity_id ?? "未识别标的";
}

function runTargetMeta(run: AgentOpsRunSummary): string {
  const parts = [run.target_symbol, run.target_market, run.node_kind].filter(
    (item): item is string => Boolean(item)
  );
  return parts.length > 0 ? parts.join(" · ") : "缺少标的信息";
}

function shortRunId(runId: string): string {
  return runId.length > 18 ? `${runId.slice(0, 18)}...` : runId;
}

function fallbackDiagnostic() {
  return {
    severity: "info" as const,
    title: "当前 run 只有基础 trace",
    summary: "这条历史 run 没有记录诊断摘要，可展开具体 step 查看输入、输出和证据。",
    tags: [],
    slowest_step_name: null,
    slowest_step_latency_ms: null,
    next_actions: ["查看 trace step 详情"]
  };
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

function formatMoney(value: number, currency: string): string {
  const normalized = currency.toUpperCase();
  if (normalized === "CNY") {
    return `¥${value.toFixed(6)}`;
  }
  if (normalized === "USD") {
    return `$${value.toFixed(6)}`;
  }
  return `${normalized} ${value.toFixed(6)}`;
}

function toErrorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message;
  }
  return "unknown error";
}
