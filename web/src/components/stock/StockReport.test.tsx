import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeEdge, makeEntity, makeEvidence, makeOverlapGroup, makeRunDetail } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { StockDetailData } from "../../hooks/use-stock-detail";
import * as markdown from "../../lib/markdown";
import { StockReport } from "./StockReport";

describe("StockReport", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders eight report sections and evidence entries", () => {
    const onEvidenceClick = vi.fn();

    render(<StockReport detail={makeDetail()} onEvidenceClick={onEvidenceClick} />);

    expect(screen.getByRole("heading", { name: "AAPL 深度报告" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "① 摘要" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "② 变化" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "③ 产业链" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "④ 分类情报" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "⑤ 方向" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "⑥ 研究假设" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "⑦ 关注点（仅供参考）" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "⑧ 来源清单" })).toBeInTheDocument();
    expect(screen.getAllByText("Apple supplier pressure is easing.")).toHaveLength(2);
    expect(screen.getByText("Consumer Electronics (基于推断)")).toBeInTheDocument();
    expect(screen.getByText("https://example.com/evidence-1")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(REDLINE_PATTERN);

    fireEvent.click(
      within(screen.getByLabelText("报告情报 Supplier update")).getByRole("button", {
        name: "查看证据"
      })
    );
    expect(onEvidenceClick).toHaveBeenCalledWith(["evidence-1"]);
  });

  it("exports markdown with a symbol based filename", () => {
    const stockReportToMarkdown = vi
      .spyOn(markdown, "stockReportToMarkdown")
      .mockReturnValue("# AAPL 深度报告");
    const downloadMarkdown = vi
      .spyOn(markdown, "downloadMarkdown")
      .mockImplementation(() => undefined);

    render(<StockReport detail={makeDetail()} />);

    fireEvent.click(screen.getByRole("button", { name: "导出 Markdown" }));

    expect(stockReportToMarkdown).toHaveBeenCalled();
    expect(downloadMarkdown).toHaveBeenCalledWith(
      "AAPL-report.md",
      "# AAPL 深度报告"
    );
    expect(screen.getByRole("status")).toHaveTextContent("AAPL-report.md");
  });
});

function makeDetail(): StockDetailData {
  const entity = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const evidence = { ...makeEvidence(), title: "Supplier evidence" };
  const run = makeRunDetail(entity, evidence);
  const tsm = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
  const segment = makeEntity({
    id: "segment-consumer",
    name: "Consumer Electronics",
    node_type: "segment",
    symbol: null
  });
  return {
    entityId: "entity-aapl",
    positionId: "position-1",
    runId: "run-1",
    run,
    entity,
    evidences: run.evidences,
    intelItems: run.intel_items,
    thesis: run.thesis,
    neighbors: [
      makeEdge("edge-source", tsm, "source_backed", ["evidence-1"]),
      makeEdge("edge-inferred", segment, "inferred", [])
    ],
    overlaps: [makeOverlapGroup()],
    relevancePath: [entity, tsm]
  };
}
