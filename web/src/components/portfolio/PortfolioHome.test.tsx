import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { makeOverlapGroup } from "../../test/m3-fixtures";
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

const listPositionsMock = vi.mocked(client.listPositions);
const createPositionMock = vi.mocked(client.createPosition);
const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("PortfolioHome", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    getSharedSuppliersMock.mockResolvedValue([]);
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

  it("filters positions by global search and topbar filters", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple", kind: "owned" }),
      makePosition({ id: "position-2", symbol: "MSFT", name: "Microsoft", kind: "watching" })
    ]);

    render(<PortfolioHome />);

    const list = await screen.findByLabelText("持仓列表");
    expect(within(list).getByText("AAPL")).toBeInTheDocument();
    expect(within(list).getByText("MSFT")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("全局搜索"), {
      target: { value: "msft" }
    });
    expect(within(list).queryByText("AAPL")).not.toBeInTheDocument();
    expect(within(list).getByText("MSFT")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "筛选" }));
    fireEvent.change(screen.getByLabelText("持仓类型筛选"), {
      target: { value: "owned" }
    });
    expect(await screen.findByText("没有匹配的持仓")).toBeInTheDocument();
  });

  it("opens a launch readiness status panel from the topbar", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);

    render(<PortfolioHome />);

    await screen.findByLabelText("持仓列表");
    fireEvent.click(screen.getByRole("button", { name: "产品状态" }));

    const panel = screen.getByLabelText("产品状态面板");
    expect(within(panel).getByText("本地优先")).toBeInTheDocument();
    expect(within(panel).getByText("非荐股")).toBeInTheDocument();
    expect(within(panel).getByText("证据化")).toBeInTheDocument();
    expect(within(panel).getByText("门禁")).toBeInTheDocument();
  });

  it("shows an empty state when there are no positions", async () => {
    listPositionsMock.mockResolvedValue([]);

    render(<PortfolioHome />);

    expect(await screen.findByText("暂无持仓")).toBeInTheDocument();
  });

  it("retries loading positions after an API failure", async () => {
    listPositionsMock.mockRejectedValueOnce(new Error("GET /positions failed: 503"));
    listPositionsMock.mockResolvedValueOnce([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);

    render(<PortfolioHome />);

    expect(await screen.findByText("GET /positions failed: 503")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重新加载持仓" }));

    const list = await screen.findByLabelText("持仓列表");
    expect(within(list).getByText("AAPL")).toBeInTheDocument();
    expect(listPositionsMock).toHaveBeenCalledTimes(2);
  });

  it("mounts overlap and supply-chain cross insights below the position list", async () => {
    listPositionsMock.mockResolvedValue([
      makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" })
    ]);
    getOverlapsMock.mockResolvedValue([makeOverlapGroup({ basis: "source_backed" })]);

    render(<PortfolioHome />);

    await screen.findByLabelText("持仓列表");
    const centralInsights = await screen.findByLabelText("组合中央洞察");
    const overlapPanel = await screen.findByLabelText("组合重叠提示");
    const crossPanel = await screen.findByTestId("supply-chain-cross-panel");

    expect(centralInsights).toContainElement(overlapPanel);
    expect(centralInsights).toContainElement(crossPanel);
    expect(within(overlapPanel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(overlapPanel).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(await screen.findByLabelText("组合 Brief")).not.toHaveTextContent("Consumer Electronics");
    expect(screen.getByText("Apple supplier pressure is easing.")).toBeInTheDocument();
  });

  it("creates a position and refreshes the list", async () => {
    const firstPosition = makePosition({ id: "position-1", symbol: "AAPL", name: "Apple" });
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
    fireEvent.click(screen.getByRole("button", { name: "+ 添加持仓" }));
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "MSFT" } });
    fireEvent.change(screen.getByLabelText("Market"), { target: { value: "US" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Microsoft" } });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "watching" } });
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

  it("creates a company-name-only position when the ticker is unknown", async () => {
    const createdPosition = makePosition({
      id: "position-spacex", symbol: "SpaceX", name: "SpaceX", kind: "watching"
    });
    listPositionsMock.mockResolvedValueOnce([]);
    listPositionsMock.mockResolvedValueOnce([createdPosition]);
    createPositionMock.mockResolvedValue(createdPosition);

    render(<PortfolioHome />);

    await screen.findByText("暂无持仓");
    fireEvent.click(screen.getByRole("button", { name: "+ 添加持仓" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "SpaceX" } });
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "watching" } });
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));

    await waitFor(() =>
      expect(createPositionMock).toHaveBeenCalledWith({
        symbol: null,
        market: "US",
        name: "SpaceX",
        kind: "watching"
      })
    );
    expect(await screen.findByText("SpaceX")).toBeInTheDocument();
  });

  it("requires either symbol or company name before creating a position", async () => {
    listPositionsMock.mockResolvedValue([]);

    render(<PortfolioHome />);

    await screen.findByText("暂无持仓");
    fireEvent.click(screen.getByRole("button", { name: "+ 添加持仓" }));
    fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));

    expect(await screen.findByText("请输入 Symbol 或公司名称")).toBeInTheDocument();
    expect(createPositionMock).not.toHaveBeenCalled();
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
    expect(screen.getByRole("button", { name: "重新研究 AAPL" })).toBeInTheDocument();
    const overlapPanel = await screen.findByLabelText("组合重叠提示");
    expect(within(overlapPanel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(getOverlapsMock).toHaveBeenCalledTimes(2);
    expect(getPortfolioBriefMock).toHaveBeenCalledTimes(2);
  });

});
