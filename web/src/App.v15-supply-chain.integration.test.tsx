import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeEdge,
  makeEntity,
  makeEvidence,
  makeExpandResult,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";
import type {
  CreatePositionInput,
  EntityNode,
  Position,
  RunDetail,
  SharedSupplierGroup
} from "./types/api";

vi.mock("reactflow", () => ({
  default: () => <div data-testid="react-flow" />,
  Background: () => null,
  Controls: () => null,
  getBezierPath: () => ["M0,0 L10,10", 5, 5],
  Handle: ({ "data-testid": testId }: { "data-testid"?: string }) => (
    <span data-testid={testId} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  confirmThesis: vi.fn(),
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getEvidence: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRepresentatives: vi.fn(),
  getRun: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

const createPositionMock = vi.mocked(client.createPosition);
const expandEntityMock = vi.mocked(client.expandEntity);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRunMock = vi.mocked(client.getRun);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);
const startRunMock = vi.mocked(client.startRun);

describe("App V1.5 supply chain path", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("analyzes two researched holdings into shared suppliers and correlation", async () => {
    const serverPositions: Position[] = [];
    const entities = {
      aapl: makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" }),
      msft: makeEntity({ id: "entity-msft", name: "Microsoft", symbol: "MSFT" }),
      tsmc: makeEntity({ id: "entity-tsmc", name: "Taiwan Semiconductor", symbol: "TSM" })
    };
    const expandedSeeds = new Set<string>();

    listPositionsMock.mockImplementation(async () => clonePositions(serverPositions));
    createPositionMock.mockImplementation(async (input) => addPosition(serverPositions, input));
    startRunMock.mockImplementation(async (positionId) => startServerRun(serverPositions, positionId, entities));
    getRunMock.mockImplementation(async (runId) => makeRun(runId, entities));
    expandEntityMock.mockImplementation(async (entityId, positionId) => {
      expandedSeeds.add(`${positionId}:${entityId}`);
      return makeExpandResult([makeEdge("edge-tsmc", entities.tsmc, "source_backed", ["evidence-1"])]);
    });
    getOverlapsMock.mockResolvedValue([]);
    getSharedSuppliersMock.mockImplementation(async () =>
      hasBothSeeds(expandedSeeds) ? [makeSharedSupplier()] : []
    );
    getCorrelationMatrixMock.mockImplementation(async () =>
      hasBothSeeds(expandedSeeds)
        ? {
            positions: [
              { position_id: "position-aapl", symbol: "AAPL", label: "Apple" },
              { position_id: "position-msft", symbol: "MSFT", label: "Microsoft" }
            ],
            cells: [
              {
                a_position_id: "position-aapl",
                b_position_id: "position-msft",
                shared_count: 1,
                shared_suppliers: ["Taiwan Semiconductor"]
              }
            ]
          }
        : { positions: [], cells: [] }
    );
    getPortfolioBriefMock.mockResolvedValue({
      generated_at: "2026-07-02T00:00:00Z",
      positions: [],
      overlaps: [],
      run_health: makeRunHealth()
    });

    render(<App />);

    await addHolding("AAPL", "Apple");
    await addHolding("MSFT", "Microsoft");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    await waitFor(() => expect(startRunMock).toHaveBeenCalledWith("position-aapl"));
    expect(
      await screen.findByRole("button", { name: "查看图谱 AAPL" })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "开始研究 MSFT" }));
    await waitFor(() => expect(startRunMock).toHaveBeenCalledWith("position-msft"));
    expect(
      await screen.findByRole("button", { name: "查看图谱 MSFT" })
    ).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "分析组合供应链" }));

    await waitFor(() => expect(expandEntityMock).toHaveBeenCalledTimes(2));
    expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-aapl");
    expect(expandEntityMock).toHaveBeenCalledWith("entity-msft", "position-msft");
    const sharedPanel = await screen.findByTestId("shared-suppliers-panel");
    expect(within(sharedPanel).getByText("Taiwan Semiconductor")).toBeInTheDocument();
    expect(within(sharedPanel).getByText("AAPL / MSFT")).toBeInTheDocument();
    const matrixPanel = await screen.findByTestId("correlation-matrix-panel");
    expect(
      within(screen.getByTestId("correlation-cell-position-aapl-position-msft")).getByText("1")
    ).toBeInTheDocument();
    expect(matrixPanel).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});

async function addHolding(symbol: string, name: string): Promise<void> {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: name } });
  fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
  await screen.findByText(symbol);
}

function addPosition(positions: Position[], input: CreatePositionInput): Position {
  const symbol = input.symbol ?? "";
  const position = makePosition({
    id: `position-${symbol.toLowerCase()}`,
    symbol,
    name: input.name ?? null
  });
  positions.push(position);
  return { ...position };
}

function startServerRun(
  positions: Position[],
  positionId: string,
  entities: Record<"aapl" | "msft" | "tsmc", EntityNode>
): { run_id: string; status: "awaiting_confirmation"; thesis_id: string } {
  const isMsft = positionId === "position-msft";
  const runId = isMsft ? "run-msft" : "run-aapl";
  const entity = isMsft ? entities.msft : entities.aapl;
  const position = positions.find((item) => item.id === positionId);
  if (position) {
    position.latest_run_id = runId;
    position.latest_run_status = "awaiting_confirmation";
    position.latest_run_entity = entity;
  }
  return { run_id: runId, status: "awaiting_confirmation", thesis_id: "thesis-1" };
}

function makeRun(
  runId: string,
  entities: Record<"aapl" | "msft" | "tsmc", EntityNode>
): RunDetail {
  return {
    ...makeRunDetail(runId === "run-msft" ? entities.msft : entities.aapl, makeEvidence()),
    run_id: runId
  };
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

function hasBothSeeds(expandedSeeds: Set<string>): boolean {
  return (
    expandedSeeds.has("position-aapl:entity-aapl") &&
    expandedSeeds.has("position-msft:entity-msft")
  );
}

function clonePositions(positions: Position[]): Position[] {
  return positions.map((position) => ({
    ...position,
    latest_run_entity: position.latest_run_entity
      ? { ...position.latest_run_entity }
      : position.latest_run_entity
  }));
}
