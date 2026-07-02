import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { REDLINE_PATTERN } from "./test/redline";

describe("App redesign integration path", () => {
  it("opens graph, stock detail, evidence, and confirmation without redline copy", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 NVDA" }));
    expect(screen.getByRole("heading", { name: "Research Graph — NVDA" })).toBeInTheDocument();

    fireEvent.click(screen.getByTitle("点击展开产业链（懒加载）"));
    expect(screen.getAllByText("ASML").length).toBeGreaterThan(0);

    const relationships = screen.getByLabelText("关系清单");
    fireEvent.click(within(relationships).getAllByRole("button", { name: "查看证据" })[0]);
    expect(screen.getByRole("dialog", { name: "证据抽屉" })).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog", { name: "证据抽屉" })).getByRole("button", { name: "关闭" }));

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));
    const detail = screen.getByRole("dialog", { name: "个股详情" });
    expect(within(detail).getByText("STOCK DETAIL / THESIS")).toBeInTheDocument();
    fireEvent.click(within(detail).getByRole("button", { name: "确认 thesis 假设" }));
    expect(within(detail).getByText("✓ 已确认：假设已纳入跟踪基线")).toBeInTheDocument();

    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);
  });
});
