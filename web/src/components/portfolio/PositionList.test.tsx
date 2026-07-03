import type { ComponentProps } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EntityNode, Position } from "../../types/api";
import { PositionList } from "./PositionList";

describe("PositionList", () => {
  it("merges market and kind under the symbol and renders status chips", () => {
    render(<PositionList {...props({ positions: statusPositions() })} />);

    const header = screen.getByText("标的").parentElement as HTMLElement;
    expect(within(header).getByText("状态")).toBeInTheDocument();
    expect(within(header).getByText("RUN")).toBeInTheDocument();
    expect(within(header).queryByText("市场")).not.toBeInTheDocument();
    expect(within(header).queryByText("类型")).not.toBeInTheDocument();

    const list = screen.getByLabelText("持仓列表");
    expect(within(list).getAllByText("US · owned").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("研究状态 AAPL")).toHaveTextContent("已研究");
    expect(screen.getByLabelText("研究状态 MSFT")).toHaveTextContent("研究中");
    expect(screen.getByLabelText("研究状态 SONY")).toHaveTextContent("未研究");
    expect(screen.getByLabelText("研究状态 TSLA")).toHaveTextContent("待解析");
  });

  it("uses the row as the primary graph entry while keeping buttons usable", () => {
    const onViewGraph = vi.fn();
    const onStartRun = vi.fn();
    render(
      <PositionList
        {...props({
          onStartRun,
          onViewGraph,
          positions: [researchedPosition("position-aapl", "AAPL")]
        })}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "打开图谱 AAPL" }));
    expect(onViewGraph).toHaveBeenCalledWith("position-aapl", "run-aapl", entity("entity-aapl"));

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 AAPL" }));
    expect(onViewGraph).toHaveBeenCalledTimes(2);

    const actions = screen.getByRole("button", { name: "查看图谱 AAPL" }).parentElement;
    expect(actions).toHaveClass("row-actions-muted");
    fireEvent.click(screen.getByRole("button", { name: "重新研究 AAPL" }));
    expect(onStartRun).toHaveBeenCalledWith("position-aapl");
  });
});

function props(overrides: Partial<ComponentProps<typeof PositionList>> = {}) {
  return {
    activePositionId: null,
    onStartRun: vi.fn(),
    onViewGraph: vi.fn(),
    positions: [],
    runEntity: null,
    runId: null,
    runPositionId: null,
    runStatus: "idle",
    ...overrides
  };
}

function statusPositions(): Position[] {
  return [
    researchedPosition("position-aapl", "AAPL", "owned"),
    { ...researchedPosition("position-msft", "MSFT", "watching"), latest_run_status: "running" },
    basePosition("position-sony", "SONY", "watching"),
    { ...basePosition("position-tsla", "TSLA", "owned"), latest_run_id: "run-tsla" }
  ];
}

function researchedPosition(
  id: string,
  symbol: string,
  kind: Position["kind"] = "owned"
): Position {
  return {
    ...basePosition(id, symbol, kind),
    latest_run_entity: entity(`entity-${symbol.toLowerCase()}`, symbol),
    latest_run_id: `run-${symbol.toLowerCase()}`,
    latest_run_status: "completed"
  };
}

function basePosition(id: string, symbol: string, kind: Position["kind"]): Position {
  return {
    id,
    symbol,
    market: "US",
    name: `${symbol} Inc.`,
    kind
  };
}

function entity(id: string, symbol = "AAPL"): EntityNode {
  return { id, name: `${symbol} Inc.`, node_type: "company", symbol, market: "US" };
}
