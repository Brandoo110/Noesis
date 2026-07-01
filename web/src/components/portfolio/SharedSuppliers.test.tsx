import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { makeEntity, makePosition } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { Position, SharedSupplierGroup } from "../../types/api";
import { SharedSuppliers } from "./SharedSuppliers";

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn(),
  getSharedSuppliers: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);

describe("SharedSuppliers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders shared suppliers with basis labels and redline-safe copy", async () => {
    getSharedSuppliersMock.mockResolvedValue([makeSharedSupplier()]);

    render(
      <SharedSuppliers
        activeRun={{ entity: null, positionId: null }}
        positions={seededPositions()}
      />
    );

    const panel = await screen.findByTestId("shared-suppliers-panel");

    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(within(panel).getByText("Taiwan Semiconductor")).toBeInTheDocument();
    expect(within(panel).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(within(panel).getByText("基于推断")).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("shows an empty shared supplier state", async () => {
    getSharedSuppliersMock.mockResolvedValue([]);

    render(
      <SharedSuppliers
        activeRun={{ entity: null, positionId: null }}
        positions={seededPositions()}
      />
    );

    expect(await screen.findByText("暂无共享上游供应商")).toBeInTheDocument();
  });

  it("expands researched position seeds on demand and refreshes", async () => {
    const onAnalyzed = vi.fn();
    getSharedSuppliersMock.mockResolvedValueOnce([]);
    getSharedSuppliersMock.mockResolvedValueOnce([makeSharedSupplier()]);
    expandEntityMock.mockResolvedValue({
      entity_id: "entity-aapl",
      run_id: "run-expand",
      status: "completed",
      edges: []
    });

    render(
      <SharedSuppliers
        activeRun={{ entity: null, positionId: null }}
        onAnalyzed={onAnalyzed}
        positions={seededPositions()}
      />
    );

    await screen.findByText("暂无共享上游供应商");
    fireEvent.click(screen.getByRole("button", { name: "分析组合供应链" }));

    await waitFor(() => expect(expandEntityMock).toHaveBeenCalledTimes(2));
    expect(expandEntityMock).toHaveBeenNthCalledWith(1, "entity-aapl", "position-aapl");
    expect(expandEntityMock).toHaveBeenNthCalledWith(2, "entity-msft", "position-msft");
    expect(await screen.findByText("Taiwan Semiconductor")).toBeInTheDocument();
    expect(onAnalyzed).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "分析组合供应链" }));
    await waitFor(() => expect(getSharedSuppliersMock).toHaveBeenCalledTimes(3));
    expect(expandEntityMock).toHaveBeenCalledTimes(2);
  });
});

function seededPositions(): Position[] {
  return [
    makePosition({
      id: "position-aapl",
      symbol: "AAPL",
      latest_run_entity: makeEntity({ id: "entity-aapl", symbol: "AAPL" }),
      latest_run_id: "run-aapl",
      latest_run_status: "completed"
    }),
    makePosition({
      id: "position-msft",
      symbol: "MSFT",
      latest_run_entity: makeEntity({ id: "entity-msft", symbol: "MSFT" }),
      latest_run_id: "run-msft",
      latest_run_status: "completed"
    })
  ];
}

function makeSharedSupplier(): SharedSupplierGroup {
  return {
    supplier_id: "entity-tsmc",
    supplier_name: "Taiwan Semiconductor",
    node_type: "company",
    basis: "inferred",
    positions: [
      {
        position_id: "position-aapl",
        symbol: "AAPL",
        entity_id: "entity-aapl",
        confidence: 0.91
      },
      {
        position_id: "position-msft",
        symbol: "MSFT",
        entity_id: "entity-msft",
        confidence: 0.62
      }
    ]
  };
}
