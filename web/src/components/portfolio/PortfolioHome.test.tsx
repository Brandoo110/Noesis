import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type { Position, RunDetail } from "../../types/api";
import { PortfolioHome } from "./PortfolioHome";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  getRun: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

vi.mock("../graph/GraphExplorer", () => ({
  GraphExplorer: ({
    positionId,
    seedEntity
  }: {
    positionId: string;
    seedEntity: { id: string };
  }) => <div data-testid="graph-explorer">{`${positionId}:${seedEntity.id}`}</div>
}));

const listPositionsMock = vi.mocked(client.listPositions);
const createPositionMock = vi.mocked(client.createPosition);
const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("PortfolioHome", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders positions from the API", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);

    render(<PortfolioHome />);

    const list = await screen.findByLabelText("持仓列表");

    expect(within(list).getByText("AAPL")).toBeInTheDocument();
    expect(within(list).getByText("Apple")).toBeInTheDocument();
    expect(within(list).getByText("owned")).toBeInTheDocument();
  });

  it("shows an empty state when there are no positions", async () => {
    listPositionsMock.mockResolvedValue([]);

    render(<PortfolioHome />);

    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
  });

  it("creates a position and refreshes the list", async () => {
    const firstPosition = makePosition({
      id: "position-1",
      symbol: "AAPL",
      name: "Apple"
    });
    const createdPosition = makePosition({
      id: "position-2",
      symbol: "MSFT",
      name: "Microsoft",
      kind: "watching"
    });
    listPositionsMock.mockResolvedValueOnce([firstPosition]);
    listPositionsMock.mockResolvedValueOnce([firstPosition, createdPosition]);
    createPositionMock.mockResolvedValue(createdPosition);

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.change(screen.getByLabelText("Symbol"), {
      target: { value: "MSFT" }
    });
    fireEvent.change(screen.getByLabelText("Market"), {
      target: { value: "US" }
    });
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Microsoft" }
    });
    fireEvent.change(screen.getByLabelText("Kind"), {
      target: { value: "watching" }
    });
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));

    await waitFor(() =>
      expect(createPositionMock).toHaveBeenCalledWith({
        symbol: "MSFT",
        market: "US",
        name: "Microsoft",
        kind: "watching"
      })
    );
    expect(await screen.findByText("MSFT")).toBeInTheDocument();
    expect(listPositionsMock).toHaveBeenCalledTimes(2);
  });

  it("starts research for a position and shows run status", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    startRunMock.mockResolvedValue({
      run_id: "run-1",
      status: "awaiting_confirmation",
      thesis_id: "thesis-1"
    });
    getRunMock.mockResolvedValue(makeRunDetail());

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));

    await waitFor(() => expect(startRunMock).toHaveBeenCalledWith("position-1"));
    expect(screen.getByText("awaiting_confirmation")).toBeInTheDocument();
    expect(screen.getByText("run-1")).toBeInTheDocument();
  });

  it("opens GraphExplorer when a run has a seed entity", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    startRunMock.mockResolvedValue({
      run_id: "run-1",
      status: "awaiting_confirmation",
      thesis_id: "thesis-1"
    });
    getRunMock.mockResolvedValue(makeRunDetail());

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    const graphButton = await screen.findByRole("button", {
      name: "查看图谱 AAPL"
    });
    fireEvent.click(graphButton);

    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-1:entity-aapl"
    );
  });
});

function makePosition(overrides: Partial<Position> = {}): Position {
  return {
    id: "position-1",
    symbol: "AAPL",
    market: "US",
    name: "Apple",
    kind: "owned",
    qty: null,
    cost_basis: null,
    ...overrides
  };
}

function makeRunDetail(): RunDetail {
  return {
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1",
    entity: {
      id: "entity-aapl",
      name: "Apple Inc.",
      node_type: "company",
      symbol: "AAPL",
      market: "US"
    },
    evidences: [],
    intel_items: [],
    thesis: null
  };
}
