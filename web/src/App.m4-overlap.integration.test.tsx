import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import { makeEntity, makeEvidence, makeOverlapGroup, makeRunDetail } from "./test/m3-fixtures";
import type { CreatePositionInput, EntityNode, Position, RunDetail } from "./types/api";

vi.mock("reactflow", async () => ({
  default: ({ nodeTypes, nodes }: FlowProps) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return (
          <Node
            data={node.data}
            dragging={false}
            id={node.id}
            isConnectable={false}
            key={node.id}
            selected={false}
            type={node.type}
            xPos={0}
            yPos={0}
            zIndex={0}
          />
        );
      })}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  Handle: ({ "data-testid": testId, type }: HandleProps) => (
    <span data-testid={testId} data-type={type} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  confirmThesis: vi.fn(),
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getEvidence: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getRelevance: vi.fn(),
  getRepresentatives: vi.fn(),
  getRun: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

interface FlowProps {
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

interface HandleProps {
  "data-testid"?: string;
  type: string;
}

const confirmThesisMock = vi.mocked(client.confirmThesis);
const createPositionMock = vi.mocked(client.createPosition);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getRunMock = vi.mocked(client.getRun);
const listPositionsMock = vi.mocked(client.listPositions);
const startRunMock = vi.mocked(client.startRun);

describe("App M4 overlap path", () => {
  let consoleErrorMock: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    consoleErrorMock = vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleErrorMock.mockRestore();
  });

  it("walks two holdings into portfolio and stock-detail overlap hints", async () => {
    const positions: Position[] = [];
    const statusByRun = new Map<string, RunDetail["status"]>();
    const entities = {
      aapl: makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" }),
      msft: makeEntity({ id: "entity-msft", name: "Microsoft", symbol: "MSFT" })
    };
    const overlap = makeOverlapGroup({
      positions: [
        { position_id: "position-aapl", symbol: "AAPL", entity_id: "entity-aapl", confidence: 0.9 },
        { position_id: "position-msft", symbol: "MSFT", entity_id: "entity-msft", confidence: 0.7 }
      ]
    });

    listPositionsMock.mockImplementation(async () => positions);
    createPositionMock.mockImplementation(async (input) => addPosition(positions, input));
    startRunMock.mockImplementation(async (positionId) => {
      const runId = positionId === "position-aapl" ? "run-aapl" : "run-msft";
      statusByRun.set(runId, "awaiting_confirmation");
      return { run_id: runId, status: "awaiting_confirmation", thesis_id: "thesis-1" };
    });
    getRunMock.mockImplementation(async (runId) =>
      makeRunFor(runId, runId === "run-msft" ? entities.msft : entities.aapl, statusByRun)
    );
    getOverlapsMock.mockImplementation(async () =>
      statusByRun.size >= 2 ? [overlap] : []
    );
    getNeighborsMock.mockResolvedValue({ entity_id: "entity-msft", edges: [] });
    getRelevanceMock.mockResolvedValue({
      entity_id: "entity-msft",
      position_id: "position-msft",
      path: [entities.msft]
    });
    confirmThesisMock.mockImplementation(async () => {
      statusByRun.set("run-msft", "completed");
      return { run_id: "run-msft", status: "completed", thesis_id: "thesis-1" };
    });

    render(<App />);

    await addHolding("AAPL", "Apple");
    await addHolding("MSFT", "Microsoft");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    await screen.findByText("run-aapl");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 MSFT" }));
    await screen.findByText("run-msft");

    const panel = await screen.findByLabelText("组合重叠提示");
    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(within(panel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(panel).getByText("AAPL / MSFT")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 MSFT" }));
    fireEvent.click(await screen.findByRole("button", { name: "详情 MSFT" }));
    const detailOverlap = await screen.findByLabelText("组合重叠关系");
    expect(within(detailOverlap).getByText("AAPL")).toBeInTheDocument();
    expect(within(detailOverlap).getByText("Consumer Electronics")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "确认 thesis 假设" }));
    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument());
    expect(document.body.textContent).not.toMatch(
      /买入|卖出|加仓|减仓|目标价|建议分散|调整配置|再平衡/
    );
    expect(consoleErrorMock).not.toHaveBeenCalled();
  });
});

async function addHolding(symbol: string, name: string): Promise<void> {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: name } });
  fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
  await screen.findByText(symbol);
}

function addPosition(positions: Position[], input: CreatePositionInput): Position {
  const row = {
    id: `position-${input.symbol.toLowerCase()}`,
    symbol: input.symbol,
    market: input.market,
    name: input.name ?? null,
    kind: input.kind ?? "owned",
    qty: null,
    cost_basis: null
  };
  positions.push(row);
  return row;
}

function makeRunFor(
  runId: string,
  entity: EntityNode,
  statuses: Map<string, RunDetail["status"]>
): RunDetail {
  return {
    ...makeRunDetail(entity, makeEvidence()),
    run_id: runId,
    status: statuses.get(runId) ?? "awaiting_confirmation"
  };
}
