import { afterEach, describe, expect, it, vi } from "vitest";

import { getOverlaps, getPortfolioBrief } from "./client";

describe("portfolio api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses getOverlaps response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            segment_id: "segment-consumer",
            segment_name: "Consumer Electronics",
            node_type: "segment",
            basis: "inferred",
            positions: [
              {
                position_id: "position-aapl",
                symbol: "AAPL",
                entity_id: "entity-aapl",
                confidence: 0.9
              },
              {
                position_id: "position-msft",
                symbol: "MSFT",
                entity_id: "entity-msft",
                confidence: 0.7
              }
            ]
          }
        ]),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getOverlaps()).resolves.toMatchObject([
      {
        segment_id: "segment-consumer",
        basis: "inferred",
        positions: [{ symbol: "AAPL" }, { symbol: "MSFT" }]
      }
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/portfolio/overlaps", {
      headers: { "Content-Type": "application/json" }
    });
  });

  it("throws when getOverlaps fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("error", { status: 502 }))
    );

    await expect(getOverlaps()).rejects.toThrow(
      "GET /portfolio/overlaps failed: 502"
    );
  });

  it("parses getPortfolioBrief response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-28T00:00:00Z",
          positions: [
            {
              position_id: "position-aapl",
              symbol: "AAPL",
              name: "Apple",
              thesis_summary: "Apple supplier pressure is easing.",
              thesis_status: "confirmed"
            },
            {
              position_id: "position-msft",
              symbol: "MSFT",
              name: null,
              thesis_summary: null,
              thesis_status: null
            }
          ],
          overlaps: [],
          run_health: {
            total_latest_runs: 2,
            running: 0,
            awaiting_confirmation: 0,
            completed: 2,
            failed: 0,
            completed_without_thesis: 0,
            degraded_runs: 0,
            failed_runs: [],
            degraded_reasons: []
          }
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPortfolioBrief()).resolves.toMatchObject({
      generated_at: "2026-06-28T00:00:00Z",
      positions: [{ symbol: "AAPL" }, { symbol: "MSFT" }],
      run_health: { completed: 2 }
    });
    expect(fetchMock).toHaveBeenCalledWith("/portfolio/brief", {
      headers: { "Content-Type": "application/json" }
    });
  });

  it("throws when getPortfolioBrief fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("error", { status: 500 }))
    );

    await expect(getPortfolioBrief()).rejects.toThrow(
      "GET /portfolio/brief failed: 500"
    );
  });
});
