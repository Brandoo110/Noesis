import { afterEach, describe, expect, it, vi } from "vitest";

import { getCorrelationMatrix, getSharedSuppliers } from "./client";

describe("supply chain api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses getSharedSuppliers response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            supplier_id: "entity-tsmc",
            supplier_name: "Taiwan Semiconductor",
            node_type: "company",
            basis: "source_backed",
            positions: [
              {
                position_id: "position-aapl",
                symbol: "AAPL",
                entity_id: "entity-aapl",
                confidence: 0.91
              }
            ]
          }
        ]),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getSharedSuppliers()).resolves.toEqual([
      {
        supplier_id: "entity-tsmc",
        supplier_name: "Taiwan Semiconductor",
        node_type: "company",
        basis: "source_backed",
        positions: [
          {
            position_id: "position-aapl",
            symbol: "AAPL",
            entity_id: "entity-aapl",
            confidence: 0.91
          }
        ]
      }
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/portfolio/shared-suppliers", {
      headers: { "Content-Type": "application/json" }
    });
  });

  it("throws when getSharedSuppliers fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("error", { status: 503 }))
    );

    await expect(getSharedSuppliers()).rejects.toThrow(
      "GET /portfolio/shared-suppliers failed: 503"
    );
  });

  it("parses getCorrelationMatrix response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          positions: [
            { position_id: "position-aapl", symbol: "AAPL", label: "AAPL" },
            { position_id: "position-msft", symbol: null, label: "Microsoft" }
          ],
          cells: [
            {
              a_position_id: "position-aapl",
              b_position_id: "position-msft",
              shared_count: 2,
              shared_suppliers: ["TSMC", "Samsung"]
            }
          ]
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCorrelationMatrix()).resolves.toEqual({
      positions: [
        { position_id: "position-aapl", symbol: "AAPL", label: "AAPL" },
        { position_id: "position-msft", symbol: null, label: "Microsoft" }
      ],
      cells: [
        {
          a_position_id: "position-aapl",
          b_position_id: "position-msft",
          shared_count: 2,
          shared_suppliers: ["TSMC", "Samsung"]
        }
      ]
    });
    expect(fetchMock).toHaveBeenCalledWith("/portfolio/correlation", {
      headers: { "Content-Type": "application/json" }
    });
  });

  it("throws when getCorrelationMatrix fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("error", { status: 500 }))
    );

    await expect(getCorrelationMatrix()).rejects.toThrow(
      "GET /portfolio/correlation failed: 500"
    );
  });
});
