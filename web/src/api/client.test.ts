import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getMetricsSummary,
  getRunTrace,
  listPositions,
  listRuns,
  startRun
} from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses listPositions response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "position-1",
            symbol: "AAPL",
            market: "US",
            name: "Apple",
            kind: "owned",
            qty: null,
            cost_basis: null
          }
        ]),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listPositions()).resolves.toEqual([
      {
        id: "position-1",
        symbol: "AAPL",
        market: "US",
        name: "Apple",
        kind: "owned",
        qty: null,
        cost_basis: null
      }
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/positions", {
      headers: { "Content-Type": "application/json" }
    });
  });

  it("throws on non-2xx responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not found", { status: 404 }))
    );

    await expect(listPositions()).rejects.toThrow("GET /positions failed: 404");
  });

  it("includes structured backend error reason when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: "ResearchNodeError",
            message: "position not found",
            reason: "position_not_found"
          }),
          {
            status: 502,
            headers: { "Content-Type": "application/json" }
          }
        )
      )
    );

    await expect(startRun("position-missing")).rejects.toThrow(
      "POST /runs failed: 502 (position_not_found) position not found"
    );
  });

  it("parses AgentOps run list trace and metrics responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            runs: [
              {
                run_id: "run-1",
                status: "completed",
                started_at: "2026-06-26T00:00:00Z",
                ended_at: "2026-06-26T00:00:03Z",
                latency_ms: 3000,
                evidence_count: 1,
                tool_count: 2,
                cache_hit_rate: 0.5
              }
            ]
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "run-1",
            status: "completed",
            steps: [
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
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_runs: 1,
            task_completion_rate: 1,
            avg_latency_ms: 3000,
            p95_latency_ms: 3000,
            tool_success_rate: 1,
            tool_failure_rate: 0,
            retry_count: 0,
            cache_hit_rate: 0.5,
            average_token_usage: 0,
            estimated_cost_per_run: 0,
            cost_tracking_enabled: true,
            cost_currency: "CNY",
            evidence_coverage: 1,
            unsupported_claim_count: 0,
            rag_retrieval_count: 0
          }),
          { status: 200 }
        )
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listRuns()).resolves.toEqual({
      runs: [
        {
          run_id: "run-1",
          status: "completed",
          started_at: "2026-06-26T00:00:00Z",
          ended_at: "2026-06-26T00:00:03Z",
          latency_ms: 3000,
          evidence_count: 1,
          tool_count: 2,
          cache_hit_rate: 0.5
        }
      ]
    });
    await expect(getRunTrace("run-1")).resolves.toMatchObject({
      run_id: "run-1",
      steps: [{ name: "search.tavily" }]
    });
    await expect(getMetricsSummary()).resolves.toMatchObject({
      total_runs: 1,
      cache_hit_rate: 0.5
    });
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/runs", {
      headers: { "Content-Type": "application/json" }
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/runs/run-1/trace", {
      headers: { "Content-Type": "application/json" }
    });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/metrics/summary", {
      headers: { "Content-Type": "application/json" }
    });
  });

});
