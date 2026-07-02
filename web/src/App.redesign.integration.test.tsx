import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { REDLINE_PATTERN } from "./test/redline";

describe("Noesis redesign shell", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    vi.useRealTimers();
  });

  it("walks the redesigned portfolio, graph, drawers, AgentOps, and redline copy", async () => {
    render(<App />);

    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "持仓" })).toBeInTheDocument();
    expect(screen.getByLabelText("组合 Brief")).toBeInTheDocument();
    expect(screen.getByLabelText("相关性矩阵")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ 添加持仓" }));
    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "AAPL" } });
    fireEvent.change(screen.getByLabelText("公司名称"), { target: { value: "苹果" } });
    fireEvent.click(screen.getByRole("button", { name: "添加" }));

    expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
    expect(screen.getByText("苹果")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "开始研究 0700" }));
    expect(screen.getByText("研究中 · intake_resolve")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(4400);
    });
    expect(screen.getByText("完成 · 无 thesis")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 0700" }));
    expect(screen.getByRole("heading", { name: "Research Graph — 0700" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "inferred" }));
    const relationships = screen.getByLabelText("关系清单");
    expect(within(relationships).getAllByText("inferred").length).toBeGreaterThan(0);
    expect(within(relationships).queryByText("source")).not.toBeInTheDocument();

    fireEvent.click(within(relationships).getAllByRole("button", { name: "查看证据" })[0]);
    const evidenceDrawer = screen.getByRole("dialog", { name: "证据抽屉" });
    expect(within(evidenceDrawer).getByText("EVIDENCE VIEWER")).toBeInTheDocument();
    fireEvent.keyDown(evidenceDrawer, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "证据抽屉" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));
    const detailDrawer = screen.getByRole("dialog", { name: "个股详情" });
    expect(within(detailDrawer).getByText("STOCK DETAIL / THESIS")).toBeInTheDocument();
    fireEvent.click(within(detailDrawer).getByRole("button", { name: "重新研究" }));
    expect(screen.getByRole("heading", { name: "持仓" })).toBeInTheDocument();

    fireEvent.click(
      within(screen.getByRole("navigation", { name: "主导航" })).getByRole("button", {
        name: "AgentOps"
      })
    );
    expect(screen.getByRole("heading", { name: "Run Trace" })).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();

    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});
