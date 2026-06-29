import { afterEach, describe, expect, it, vi } from "vitest";

import { getOverlaps, getPortfolioBrief, listPositions, startRun } from "./client";

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

    await expect(getOverlaps()).resolves.toEqual([
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
          overlaps: [
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
                }
              ]
            }
          ],
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

    await expect(getPortfolioBrief()).resolves.toEqual({
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
      overlaps: [
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
            }
          ]
        }
      ],
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
