import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type {
  EntityNode,
  PortfolioBrief,
  Position,
  RunDetail,
  RunSummary
} from "../../types/api";
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
  GraphExplorer: ({ positionId, runId }: { positionId: string; runId?: string }) => (
    <div data-testid="graph-explorer">{`${positionId}:${runId ?? "no-run"}`}</div>
  )
}));

const listPositionsMock = vi.mocked(client.listPositions);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("PortfolioHome run isolation", () => {
  it("does not show an old run graph button while another position is starting", async () => {
    const pendingB = deferred<RunSummary>();
    listPositionsMock.mockResolvedValue([
      makePosition("position-a", "AAPL", "Apple"),
      makePosition("position-b", "MSFT", "Microsoft")
    ]);
    getOverlapsMock.mockResolvedValue([]);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());
    startRunMock.mockResolvedValueOnce({
      run_id: "run-a",
      status: "awaiting_confirmation",
      thesis_id: "thesis-a"
    });
    startRunMock.mockReturnValueOnce(pendingB.promise);
    getRunMock.mockResolvedValueOnce(
      makeRunDetail("run-a", makeEntity("entity-aapl", "AAPL", "Apple Inc."))
    );
    getRunMock.mockResolvedValueOnce(
      makeRunDetail("run-b", makeEntity("entity-msft", "MSFT", "Microsoft"))
    );

    render(<PortfolioHome />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    expect(await screen.findByRole("button", { name: "查看图谱 AAPL" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始研究 MSFT" }));

    await screen.findByLabelText("研究状态 MSFT");
    expect(screen.queryByRole("button", { name: "查看图谱 MSFT" })).not.toBeInTheDocument();
    expect(screen.queryByText("run-a")).not.toBeInTheDocument();

    pendingB.resolve({
      run_id: "run-b",
      status: "awaiting_confirmation",
      thesis_id: "thesis-b"
    });

    expect(await screen.findByRole("button", { name: "查看图谱 MSFT" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看图谱 MSFT" }));
    await waitFor(() =>
      expect(screen.getByTestId("graph-explorer")).toHaveTextContent("position-b:run-b")
    );
  });
});

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolveValue: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    resolveValue = resolve;
  });
  return { promise, resolve: resolveValue };
}

function makePosition(id: string, symbol: string, name: string): Position {
  return {
    id,
    symbol,
    market: "US",
    name,
    kind: "owned",
    qty: null,
    cost_basis: null
  };
}

function makeEntity(id: string, symbol: string, name: string): EntityNode {
  return {
    id,
    name,
    node_type: "company",
    symbol,
    market: "US"
  };
}

function makeRunDetail(runId: string, entity: EntityNode): RunDetail {
  return {
    run_id: runId,
    status: "awaiting_confirmation",
    thesis_id: `thesis-${runId}`,
    entity,
    evidences: [],
    intel_items: [],
    thesis: null
  };
}

function makeBrief(): PortfolioBrief {
  return {
    generated_at: "2026-06-28T00:00:00Z",
    positions: [],
    overlaps: []
  };
}
