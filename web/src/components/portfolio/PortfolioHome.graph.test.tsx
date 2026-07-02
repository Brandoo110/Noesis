import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { PortfolioHome } from "./PortfolioHome";
import { makeBrief, makePosition, makeRunDetail } from "./PortfolioHome.test-fixtures";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  getSharedSuppliers: vi.fn(),
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
      <button onClick={onThesisConfirmed} type="button">mock confirm thesis</button>
    </div>
  )
}));

const listPositionsMock = vi.mocked(client.listPositions);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("PortfolioHome graph handoff", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    getSharedSuppliersMock.mockResolvedValue([]);
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
    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));

    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-1:entity-aapl:run-1"
    );
  });

  it("moves focus to the research workspace after opening a graph", async () => {
    const scrollIntoViewMock = vi.mocked(Element.prototype.scrollIntoView);
    scrollIntoViewMock.mockClear();
    listPositionsMock.mockResolvedValue([
      makePosition({
        id: "position-1",
        symbol: "AAPL",
        name: "Apple",
        latest_run_id: "run-latest",
        latest_run_status: "awaiting_confirmation",
        latest_run_entity: entity("entity-aapl")
      })
    ]);

    render(<PortfolioHome />);

    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    await waitFor(() =>
      expect(scrollIntoViewMock).toHaveBeenCalledWith({
        block: "start",
        behavior: "smooth"
      })
    );
    expect(screen.getByLabelText("研究工作区")).toHaveFocus();
  });

  it("keeps an opened graph locked to the run id captured at click time", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-a", symbol: "AAPL", name: "Apple" }),
      makePosition({ id: "position-b", symbol: "MSFT", name: "Microsoft" })
    ]);
    startRunMock
      .mockResolvedValueOnce({ run_id: "run-a", status: "awaiting_confirmation", thesis_id: "thesis-a" })
      .mockResolvedValueOnce({ run_id: "run-b", status: "awaiting_confirmation", thesis_id: "thesis-b" });
    getRunMock.mockResolvedValueOnce(makeRunDetail({ run_id: "run-a" }));
    getRunMock.mockResolvedValueOnce(
      makeRunDetail({ run_id: "run-b", entity: entity("entity-msft", "Microsoft", "MSFT") })
    );

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-a:entity-aapl:run-a"
    );

    fireEvent.click(screen.getByRole("button", { name: "开始研究 MSFT" }));
    await waitFor(() => expect(screen.getByText("run-b")).toBeInTheDocument());
    expect(screen.getByTestId("graph-explorer")).toHaveTextContent(
      "position-a:entity-aapl:run-a"
    );
  });

  it("restores a view graph action from the latest persisted run", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({
        id: "position-1",
        symbol: "AAPL",
        name: "Apple",
        latest_run_id: "run-latest",
        latest_run_status: "awaiting_confirmation",
        latest_run_entity: entity("entity-aapl")
      })
    ]);

    render(<PortfolioHome />);

    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-1:entity-aapl:run-latest"
    );
  });
});

function entity(id: string, name = "Apple Inc.", symbol = "AAPL") {
  return { id, name, node_type: "company" as const, symbol, market: "US" };
}
