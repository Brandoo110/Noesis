import { afterEach, describe, expect, it, vi } from "vitest";

import { getOverlaps, listPositions } from "./client";

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
});
