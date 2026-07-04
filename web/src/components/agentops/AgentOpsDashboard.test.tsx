import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type { AgentOpsRunList, MetricsSummary, RunTrace } from "../../types/api";
import { AgentOpsDashboard } from "./AgentOpsDashboard";

vi.mock("../../api/client", () => ({
  clearRuns: vi.fn(),
  getMetricsSummary: vi.fn(),
  getRunTrace: vi.fn(),
  listRuns: vi.fn()
}));

const clearRunsMock = vi.mocked(client.clearRuns);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const listRunsMock = vi.mocked(client.listRuns);

describe("AgentOpsDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders metrics runs and the selected run timeline", async () => {
    listRunsMock.mockResolvedValue(makeRunList());
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock.mockResolvedValue(makeTrace());

    render(<AgentOpsDashboard />);

    const dashboard = await screen.findByLabelText("AgentOps Dashboard");
    expect(within(dashboard).getByText("runs")).toBeInTheDocument();
    expect(within(dashboard).getAllByText("50%").length).toBeGreaterThanOrEqual(1);
    expect(within(dashboard).getAllByText("3.0s").length).toBeGreaterThanOrEqual(1);
    expect(within(dashboard).getByText("P95 latency")).toBeInTheDocument();
    expect(within(dashboard).getByText("5.0s")).toBeInTheDocument();
    expect(within(dashboard).getByText("tool success")).toBeInTheDocument();
    expect(within(dashboard).getByText("tool failure")).toBeInTheDocument();
    expect(within(dashboard).getByText("cache hit")).toBeInTheDocument();
    expect(within(dashboard).getByText("tokens/run")).toBeInTheDocument();
    expect(within(dashboard).getByText("$0.001200")).toBeInTheDocument();
    expect(within(dashboard).getByText("evidence coverage")).toBeInTheDocument();
    expect(within(dashboard).getByText("RAG retrievals")).toBeInTheDocument();
    expect(within(dashboard).getByLabelText("AgentOps run list")).toHaveTextContent(
      "run-agentops"
    );
    expect(within(dashboard).getByLabelText("AgentOps run list")).toHaveTextContent(
      "Apple Inc."
    );
    expect(within(dashboard).getByLabelText("AgentOps run list")).toHaveTextContent(
      "AAPL · US · seed"
    );
    expect(await screen.findByText("当前 run 未发现明显问题")).toBeInTheDocument();
    expect(await screen.findByText("search.tavily")).toBeInTheDocument();
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "search.tavily"
    );
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "cache miss"
    );
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "query=AAPL"
    );
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "1 docs"
    );
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "retry 0"
    );
    const guide = within(dashboard).getByLabelText("AgentOps 解读指南");
    expect(guide).toHaveTextContent("Run");
    expect(guide).toHaveTextContent("一次 Agent 执行");
    expect(guide).toHaveTextContent("Run Trace");
    expect(guide).toHaveTextContent("执行时间线");
    expect(guide).not.toHaveTextContent("面试怎么讲");
  });

  it("shows diagnostic tags on run cards", async () => {
    listRunsMock.mockResolvedValue({
      runs: [
        {
          ...makeRunList().runs[0],
          diagnostic_tags: ["degraded", "low_evidence", "no_tools"]
        }
      ]
    });
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock.mockResolvedValue(makeTrace());

    render(<AgentOpsDashboard />);

    const runCard = await screen.findByRole("button", { name: /run-agentops/ });
    expect(runCard).toHaveTextContent("降级");
    expect(runCard).toHaveTextContent("低证据");
    expect(runCard).toHaveTextContent("无工具");
  });

  it("loads the selected run trace when another run is selected", async () => {
    listRunsMock.mockResolvedValue({
      runs: [
        ...makeRunList().runs,
        { ...makeRunList().runs[0], run_id: "run-second", status: "failed" }
      ]
    });
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock
      .mockResolvedValueOnce(makeTrace())
      .mockResolvedValueOnce({
        ...makeTrace(),
        run_id: "run-second",
        steps: [{ ...makeTrace().steps[0], name: "llm.synth", status: "failed" }]
      });

    render(<AgentOpsDashboard />);

    await screen.findByText("search.tavily");
    fireEvent.click(screen.getByRole("button", { name: /run-second/ }));

    expect(await screen.findByText("llm.synth")).toBeInTheDocument();
    expect(getRunTraceMock).toHaveBeenLastCalledWith("run-second");
  });

  it("retries after a dashboard load failure", async () => {
    listRunsMock.mockRejectedValueOnce(new Error("GET /runs failed: 503"));
    listRunsMock.mockResolvedValueOnce(makeRunList());
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock.mockResolvedValue(makeTrace());

    render(<AgentOpsDashboard />);

    expect(await screen.findByText("GET /runs failed: 503")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新 AgentOps" }));

    await waitFor(() => expect(listRunsMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("search.tavily")).toBeInTheDocument();
  });

  it("paginates run list and loads a run from the next page", async () => {
    listRunsMock.mockResolvedValue({ runs: makeManyRuns(10) });
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock.mockResolvedValue(makeTrace());

    render(<AgentOpsDashboard />);

    await screen.findByText("run-page-1");
    expect(screen.queryByText("run-page-9")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下一页" }));

    expect(await screen.findByText("run-page-9")).toBeInTheDocument();
    expect(getRunTraceMock).toHaveBeenLastCalledWith("run-page-9");
  });

  it("filters trace steps and expands step diagnostics", async () => {
    listRunsMock.mockResolvedValue(makeRunList());
    getMetricsSummaryMock.mockResolvedValue(makeMetrics());
    getRunTraceMock.mockResolvedValue(makeProblemTrace());

    render(<AgentOpsDashboard />);

    await screen.findByText("llm.synth");

    fireEvent.click(screen.getByRole("button", { name: "问题" }));
    expect(screen.getByText("llm.synth")).toBeInTheDocument();
    expect(screen.queryByText("ingest")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "工具" }));
    expect(screen.getByText("search.tavily")).toBeInTheDocument();
    expect(screen.getByText("llm.synth")).toBeInTheDocument();
    expect(screen.queryByText("ingest")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "慢步骤" }));
    expect(screen.getByText("llm.synth")).toBeInTheDocument();
    expect(screen.queryByText("ingest")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "证据" }));
    expect(screen.getByText("ingest")).toBeInTheDocument();
    expect(screen.queryByText("llm.synth")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "全部" }));
    fireEvent.click(screen.getByRole("button", { name: /展开 ingest/ }));

    const detail = screen.getByLabelText("ingest step detail");
    expect(detail).toHaveTextContent("Input");
    expect(detail).toHaveTextContent("state");
    expect(detail).toHaveTextContent("Evidence");
    expect(detail).toHaveTextContent("Apple evidence");
    expect(detail).toHaveTextContent("Apple evidence snippet.");

    fireEvent.click(screen.getByRole("button", { name: /展开 llm.synth/ }));
    const errorDetail = screen.getByLabelText("llm.synth step detail");
    expect(errorDetail).toHaveTextContent("Error");
    expect(errorDetail).toHaveTextContent("ReadTimeout while calling provider");
    expect(errorDetail).toHaveTextContent("Tool / Cache");
  });

  it("clears run history after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    listRunsMock
      .mockResolvedValueOnce(makeRunList())
      .mockResolvedValueOnce({ runs: [] });
    getMetricsSummaryMock
      .mockResolvedValueOnce(makeMetrics())
      .mockResolvedValueOnce({ ...makeMetrics(), total_runs: 0 });
    getRunTraceMock.mockResolvedValue(makeTrace());
    clearRunsMock.mockResolvedValue({ deleted: { run_registry: 1 } });

    render(<AgentOpsDashboard />);

    await screen.findByText("run-agentops");
    fireEvent.click(screen.getByRole("button", { name: "清空 Run 记录" }));

    await waitFor(() => expect(clearRunsMock).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("No runs yet")).toBeInTheDocument();

    confirmSpy.mockRestore();
  });
});

function makeRunList(): AgentOpsRunList {
  return {
    runs: [
      {
        run_id: "run-agentops",
        position_id: "position-aapl",
        entity_id: "entity-aapl",
        node_kind: "seed",
        target_name: "Apple Inc.",
        target_symbol: "AAPL",
        target_market: "US",
        status: "completed",
        started_at: "2026-06-26T00:00:00Z",
        ended_at: "2026-06-26T00:00:03Z",
        latency_ms: 3000,
        evidence_count: 1,
        tool_count: 2,
        cache_hit_rate: 0.5,
        diagnostic_tags: [],
        last_step_name: "ingest",
        slowest_step_name: "ingest",
        slowest_step_latency_ms: 3000,
        has_degraded_step: false,
        has_failed_step: false,
        has_pending_confirmation: false
      }
    ]
  };
}

function makeManyRuns(count: number): AgentOpsRunList["runs"] {
  return Array.from({ length: count }, (_, index) => ({
    ...makeRunList().runs[0],
    run_id: `run-page-${index + 1}`,
    status: index % 2 === 0 ? "completed" : "failed"
  }));
}

function makeMetrics(): MetricsSummary {
  return {
    total_runs: 2,
    task_completion_rate: 0.5,
    avg_latency_ms: 3000,
    p95_latency_ms: 5000,
    tool_success_rate: 0.5,
    tool_failure_rate: 0.5,
    retry_count: 1,
    cache_hit_rate: 0.5,
    average_token_usage: 140,
    estimated_cost_per_run: 0.0012,
    evidence_coverage: 0.5,
    unsupported_claim_count: 1,
    rag_retrieval_count: 2
  };
}

function makeTrace(): RunTrace {
  return {
    run_id: "run-agentops",
    status: "completed",
    diagnostic: {
      severity: "ok",
      title: "当前 run 未发现明显问题",
      summary: "这次运行没有失败、降级、低证据或明显慢步骤。",
      tags: [],
      slowest_step_name: "ingest",
      slowest_step_latency_ms: 1000,
      next_actions: ["需要排查时可展开具体 step 查看输入、输出和证据"]
    },
    steps: [
      {
        kind: "node",
        name: "ingest",
        status: "success",
        started_at: "2026-06-26T00:00:00Z",
        ended_at: "2026-06-26T00:00:01Z",
        latency_ms: 1000,
        input_summary: "state",
        output_summary: "success",
        cache_hit: null,
        retry_count: null,
        evidence_ids: ["evidence-1"],
        error_kind: null,
        error_code: null,
        error_message: null,
        http_status: null,
        provider: null,
        model_id: null,
        token_input: null,
        token_output: null,
        estimated_cost_usd: null,
        cache_key: null,
        fallback_used: null,
        degraded_reason: null
      },
      {
        kind: "tool",
        name: "search.tavily",
        status: "success",
        started_at: "2026-06-26T00:00:00Z",
        ended_at: "2026-06-26T00:00:00Z",
        latency_ms: 120,
        input_summary: "query=AAPL",
        output_summary: "1 docs",
        cache_hit: false,
        retry_count: 0,
        evidence_ids: [],
        error_kind: null,
        error_code: null,
        error_message: null,
        http_status: null,
        provider: "search",
        model_id: null,
        token_input: 0,
        token_output: 0,
        estimated_cost_usd: 0,
        cache_key: "search:AAPL",
        fallback_used: null,
        degraded_reason: null
      }
    ],
    evidence_previews: [
      {
        evidence_id: "evidence-1",
        title: "Apple evidence",
        source: "web",
        url: "https://example.com/apple",
        snippet: "Apple evidence snippet.",
        source_tier: 2,
        published_at: null
      }
    ]
  };
}

function makeProblemTrace(): RunTrace {
  return {
    ...makeTrace(),
    diagnostic: {
      severity: "critical",
      title: "当前 run 有失败步骤",
      summary: "llm.synth 失败，建议展开该步骤查看错误和重试信息。",
      tags: ["failed", "slow"],
      slowest_step_name: "llm.synth",
      slowest_step_latency_ms: 65000,
      next_actions: ["查看失败步骤详情"]
    },
    steps: [
      ...makeTrace().steps,
      {
        kind: "tool",
        name: "llm.synth",
        status: "failed",
        started_at: "2026-06-26T00:00:01Z",
        ended_at: "2026-06-26T00:01:06Z",
        latency_ms: 65000,
        input_summary: "prompt=AAPL",
        output_summary: null,
        cache_hit: false,
        retry_count: 1,
        evidence_ids: [],
        error_kind: "timeout",
        error_code: "tool_failed",
        error_message: "ReadTimeout while calling provider",
        http_status: null,
        provider: "llm",
        model_id: "deepseek-v4-pro",
        token_input: 1200,
        token_output: 0,
        estimated_cost_usd: 0.002,
        cache_key: "llm:AAPL",
        fallback_used: null,
        degraded_reason: null
      }
    ]
  };
}
