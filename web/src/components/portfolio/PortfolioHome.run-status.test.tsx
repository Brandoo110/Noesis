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

describe("PortfolioHome run status sync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    getSharedSuppliersMock.mockResolvedValue([]);
  });

  it("keeps the previous graph available while a refreshed run is running", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({
        id: "position-1",
        symbol: "AAPL",
        name: "Apple",
        latest_run_id: "run-old",
        latest_run_status: "awaiting_confirmation",
        latest_run_entity: entity("entity-aapl-old")
      })
    ]);
    startRunMock.mockResolvedValue({ run_id: "run-new", status: "running", thesis_id: null });

    render(<PortfolioHome />);

    await screen.findByRole("button", { name: "查看图谱 AAPL" });
    fireEvent.click(screen.getByRole("button", { name: "重新研究 AAPL" }));
    await waitFor(() => expect(startRunMock).toHaveBeenCalledWith("position-1"));
    expect(screen.getByRole("button", { name: "研究中 AAPL" })).toBeDisabled();
    expect(screen.getByText("run-new")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看旧图谱 AAPL" }));
    expect(await screen.findByTestId("graph-explorer")).toHaveTextContent(
      "position-1:entity-aapl-old:run-old"
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
    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    fireEvent.click(screen.getByRole("button", { name: "mock confirm thesis" }));

    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument());
    expect(getRunMock).toHaveBeenCalledTimes(2);
  });
});

function entity(id: string) {
  return { id, name: "Apple Inc.", node_type: "company" as const, symbol: "AAPL", market: "US" };
}
