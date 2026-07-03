import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { makeEntity, makePosition } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { Position, SharedSupplierGroup } from "../../types/api";
import { SupplyChainCross } from "./SupplyChainCross";

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getSharedSuppliers: vi.fn()
}));

const expandEntityMock = vi.mocked(client.expandEntity);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);

describe("SupplyChainCross", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("merges shared suppliers and correlation into one research card", async () => {
    getSharedSuppliersMock.mockResolvedValue([makeSharedSupplier()]);
    getCorrelationMatrixMock.mockResolvedValue(makeCorrelation());

    render(
      <SupplyChainCross
        activeRun={{ entity: null, positionId: null }}
        positions={seededPositions()}
      />
    );

    const panel = await screen.findByTestId("supply-chain-cross-panel");

    expect(within(panel).getByText("AAPL × MSFT")).toBeInTheDocument();
    expect(within(panel).getByText("共享 Taiwan Semiconductor")).toBeInTheDocument();
    expect(within(panel).getByText("有出处")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "分析组合供应链" })).toBeEnabled();
    expect(within(panel).getByRole("button", { name: "查看矩阵" })).toBeEnabled();
    expect(panel.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("keeps on-demand expansion and matrix dialog available", async () => {
    const onAnalyzed = vi.fn();
    getSharedSuppliersMock.mockResolvedValueOnce([]);
    getSharedSuppliersMock.mockResolvedValueOnce([makeSharedSupplier()]);
    getCorrelationMatrixMock.mockResolvedValue(makeCorrelation());
    expandEntityMock.mockResolvedValue({
      entity_id: "entity-aapl",
      run_id: "run-expand",
      status: "completed",
      edges: []
    });

    render(
      <SupplyChainCross
        activeRun={{ entity: null, positionId: null }}
        onAnalyzed={onAnalyzed}
        positions={seededPositions()}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "分析组合供应链" }));

    await waitFor(() => expect(expandEntityMock).toHaveBeenCalledTimes(2));
    expect(onAnalyzed).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("共享 Taiwan Semiconductor")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看矩阵" }));
    expect(
      await screen.findByRole("dialog", { name: "供应链相关性矩阵" })
    ).toBeInTheDocument();
  });

  it("opens a resizable matrix drawer focused on top correlated holdings", async () => {
    getSharedSuppliersMock.mockResolvedValue([makeSharedSupplier()]);
    getCorrelationMatrixMock.mockResolvedValue(makeLargeCorrelation());

    render(
      <SupplyChainCross
        activeRun={{ entity: null, positionId: null }}
        positions={seededPositions()}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "查看矩阵" }));

    const dialog = await screen.findByRole("dialog", { name: "供应链相关性矩阵" });

    expect(dialog).toHaveClass("matrix-panel-wide");
    expect(within(dialog).getByText("重点视图：显示 4 / 9 个持仓")).toBeInTheDocument();
    expect(within(dialog).getAllByText("AAPL").length).toBeGreaterThan(1);
    expect(within(dialog).getAllByText("MSFT").length).toBeGreaterThan(1);
    expect(within(dialog).queryByText("XOM")).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "全屏" }));
    expect(dialog).toHaveClass("matrix-panel-full");

    fireEvent.click(within(dialog).getByRole("button", { name: "标准" }));
    expect(dialog).toHaveClass("matrix-panel-standard");

    fireEvent.click(within(dialog).getByRole("button", { name: "显示全部持仓" }));
    expect(within(dialog).getAllByText("XOM").length).toBeGreaterThan(1);
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
    basis: "source_backed",
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", entity_id: "entity-aapl", confidence: 0.9 },
      { position_id: "position-msft", symbol: "MSFT", entity_id: "entity-msft", confidence: 0.8 }
    ]
  };
}

function makeCorrelation() {
  return {
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", label: "Apple" },
      { position_id: "position-msft", symbol: "MSFT", label: "Microsoft" }
    ],
    cells: [{
      a_position_id: "position-aapl",
      b_position_id: "position-msft",
      shared_count: 1,
      shared_suppliers: ["Taiwan Semiconductor"]
    }]
  };
}

function makeLargeCorrelation() {
  return {
    positions: [
      { position_id: "position-aapl", symbol: "AAPL", label: "Apple" },
      { position_id: "position-msft", symbol: "MSFT", label: "Microsoft" },
      { position_id: "position-sony", symbol: "SONY", label: "Sony" },
      { position_id: "position-amd", symbol: "AMD", label: "AMD" },
      { position_id: "position-amzn", symbol: "AMZN", label: "Amazon" },
      { position_id: "position-jpm", symbol: "JPM", label: "JPMorgan" },
      { position_id: "position-nike", symbol: "NKE", label: "Nike" },
      { position_id: "position-pfe", symbol: "PFE", label: "Pfizer" },
      { position_id: "position-xom", symbol: "XOM", label: "Exxon Mobil" }
    ],
    cells: [
      {
        a_position_id: "position-aapl",
        b_position_id: "position-msft",
        shared_count: 2,
        shared_suppliers: ["Taiwan Semiconductor", "Samsung"]
      },
      {
        a_position_id: "position-aapl",
        b_position_id: "position-sony",
        shared_count: 1,
        shared_suppliers: ["Sony Semiconductor"]
      },
      {
        a_position_id: "position-msft",
        b_position_id: "position-amd",
        shared_count: 1,
        shared_suppliers: ["AMD"]
      }
    ]
  };
}
