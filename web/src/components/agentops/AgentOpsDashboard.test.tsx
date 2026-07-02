import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type { AgentOpsRunList, MetricsSummary, RunTrace } from "../../types/api";
import { AgentOpsDashboard } from "./AgentOpsDashboard";

vi.mock("../../api/client", () => ({
  getMetricsSummary: vi.fn(),
  getRunTrace: vi.fn(),
  listRuns: vi.fn()
}));

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
    expect(within(dashboard).getByText("2")).toBeInTheDocument();
    expect(within(dashboard).getByText("50%")).toBeInTheDocument();
    expect(within(dashboard).getByText("3.0s")).toBeInTheDocument();
    expect(within(dashboard).getByLabelText("AgentOps run list")).toHaveTextContent(
      "run-agentops"
    );
    expect(await screen.findByText("search.tavily")).toBeInTheDocument();
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "search.tavily"
    );
    expect(within(dashboard).getByLabelText("Run trace timeline")).toHaveTextContent(
      "cache miss"
    );
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
});

function makeRunList(): AgentOpsRunList {
  return {
    runs: [
      {
        run_id: "run-agentops",
        status: "completed",
        started_at: "2026-06-26T00:00:00Z",
        ended_at: "2026-06-26T00:00:03Z",
        latency_ms: 3000,
        evidence_count: 1,
        tool_count: 2,
        cache_hit_rate: 0.5
      }
    ]
  };
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
    rag_retrieval_count: 0
  };
}

function makeTrace(): RunTrace {
  return {
    run_id: "run-agentops",
    status: "completed",
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
        evidence_ids: ["evidence-1"]
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
        evidence_ids: []
      }
    ]
  };
}
