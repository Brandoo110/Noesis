import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { PortfolioHome } from "./PortfolioHome";
import { makeBrief, makePosition } from "./PortfolioHome.test-fixtures";

vi.mock("../../api/client", () => ({
  createPosition: vi.fn(),
  deletePosition: vi.fn(),
  resolvePosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRun: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

const deletePositionMock = vi.mocked(client.deletePosition);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);

describe("PortfolioHome empty and deletion states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    getSharedSuppliersMock.mockResolvedValue([]);
  });

  it("deletes a position after confirmation and refreshes the list", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    listPositionsMock.mockResolvedValueOnce([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    listPositionsMock.mockResolvedValueOnce([]);
    deletePositionMock.mockResolvedValue(undefined);

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "删除持仓 AAPL" }));

    await waitFor(() => expect(deletePositionMock).toHaveBeenCalledWith("position-1"));
    expect(confirmSpy).toHaveBeenCalled();
    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
    expect(listPositionsMock).toHaveBeenCalledTimes(2);
    confirmSpy.mockRestore();
  });

  it("renders the empty portfolio count and message with localized card spacing", async () => {
    listPositionsMock.mockResolvedValue([]);

    render(<PortfolioHome />);

    const emptyMessage = await screen.findByText("暂无持仓");
    expect(emptyMessage).toHaveClass("position-list-empty");
    expect(screen.getByText("0 项")).toBeInTheDocument();
    expect(screen.queryByText(/ITEMS/)).not.toBeInTheDocument();
  });
});
