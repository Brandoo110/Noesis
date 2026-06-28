import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { makeOverlapGroup } from "../../test/m3-fixtures";
import type { PortfolioBrief, Position, RunDetail } from "../../types/api";
import { PortfolioHome } from "./PortfolioHome";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

vi.mock("../graph/GraphExplorer", () => ({
  GraphExplorer: ({
    onThesisConfirmed,
    positionId,
    runId,
    seedEntity
  }: {
    onThesisConfirmed?: () => void;
    positionId: string;
    runId?: string;
    seedEntity: { id: string };
  }) => (
    <div data-testid="graph-explorer">
      <span>{`${positionId}:${seedEntity.id}:${runId ?? "no-run"}`}</span>
      <button onClick={onThesisConfirmed} type="button">
        mock confirm thesis
      </button>
    </div>
  )
}));

const listPositionsMock = vi.mocked(client.listPositions);
const createPositionMock = vi.mocked(client.createPosition);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("PortfolioHome", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
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

  it("mounts portfolio overlap hints below the position list", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    getOverlapsMock.mockResolvedValue([
      makeOverlapGroup({ basis: "source_backed" })
    ]);

    render(<PortfolioHome />);

    await screen.findByLabelText("持仓列表");
    const overlapPanel = await screen.findByLabelText("组合重叠提示");
    expect(within(overlapPanel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(overlapPanel).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(await screen.findByLabelText("组合 Brief")).toBeInTheDocument();
    expect(screen.getByText("Apple supplier pressure is easing.")).toBeInTheDocument();
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
    getOverlapsMock.mockResolvedValueOnce([]);
    getOverlapsMock.mockResolvedValueOnce([makeOverlapGroup()]);
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
    const overlapPanel = await screen.findByLabelText("组合重叠提示");
    expect(within(overlapPanel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(getOverlapsMock).toHaveBeenCalledTimes(2);
    expect(getPortfolioBriefMock).toHaveBeenCalledTimes(2);
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
      "position-1:entity-aapl:run-1"
    );
  });

  it("keeps an opened graph locked to the run id captured at click time", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-a", symbol: "AAPL", name: "Apple" }),
      makePosition({ id: "position-b", symbol: "MSFT", name: "Microsoft" })
    ]);
    startRunMock.mockResolvedValueOnce({
      run_id: "run-a",
      status: "awaiting_confirmation",
      thesis_id: "thesis-a"
    });
    startRunMock.mockResolvedValueOnce({
      run_id: "run-b",
      status: "awaiting_confirmation",
      thesis_id: "thesis-b"
    });
    getRunMock.mockResolvedValueOnce(makeRunDetail({ run_id: "run-a" }));
    getRunMock.mockResolvedValueOnce(
      makeRunDetail({
        run_id: "run-b",
        entity: {
          id: "entity-msft",
          name: "Microsoft",
          node_type: "company",
          symbol: "MSFT",
          market: "US"
        }
      })
    );

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    const graphButton = await screen.findByRole("button", {
      name: "查看图谱 AAPL"
    });
    fireEvent.click(graphButton);

    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-a:entity-aapl:run-a"
    );

    fireEvent.click(screen.getByRole("button", { name: "开始研究 MSFT" }));

    await waitFor(() => expect(screen.getByText("run-b")).toBeInTheDocument());
    expect(screen.getByTestId("graph-explorer")).toHaveTextContent(
      "position-a:entity-aapl:run-a"
    );
  });

  it("refreshes portfolio row status after thesis confirmation", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    startRunMock.mockResolvedValue({
      run_id: "run-1",
      status: "awaiting_confirmation",
      thesis_id: "thesis-1"
    });
    getRunMock.mockResolvedValueOnce(makeRunDetail());
    getRunMock.mockResolvedValueOnce(makeRunDetail({ status: "completed" }));

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    const graphButton = await screen.findByRole("button", {
      name: "查看图谱 AAPL"
    });
    fireEvent.click(graphButton);
    fireEvent.click(screen.getByRole("button", { name: "mock confirm thesis" }));

    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument());
    expect(getRunMock).toHaveBeenCalledTimes(2);
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

function makeRunDetail(overrides: Partial<RunDetail> = {}): RunDetail {
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
    thesis: null,
    ...overrides
  };
}

function makeBrief(): PortfolioBrief {
  return {
    generated_at: "2026-06-28T00:00:00Z",
    positions: [
      {
        position_id: "position-1",
        symbol: "AAPL",
        name: "Apple",
        thesis_summary: "Apple supplier pressure is easing.",
        thesis_status: "confirmed"
      }
    ],
    overlaps: [makeOverlapGroup()]
  };
}
