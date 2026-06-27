import { describe, expect, it, vi } from "vitest";

import { makeEdge, makeEntity, makeEvidence, makeOverlapGroup, makeRunDetail } from "../test/m3-fixtures";
import { REDLINE_PATTERN } from "../test/redline";
import type { StockDetailData } from "../hooks/use-stock-detail";
import { downloadMarkdown, stockReportToMarkdown } from "./markdown";

describe("stockReportToMarkdown", () => {
  it("renders an eight-section stock report without redline wording", () => {
    const markdown = stockReportToMarkdown(makeDetail());

    expect(markdown).toContain("# AAPL 深度报告");
    expect(markdown).toContain("## ① 摘要");
    expect(markdown).toContain("## ② 变化");
    expect(markdown).toContain("## ③ 产业链");
    expect(markdown).toContain("## ④ 分类情报");
    expect(markdown).toContain("## ⑤ 方向");
    expect(markdown).toContain("## ⑥ Thesis");
    expect(markdown).toContain("## ⑦ 关注点（仅供参考）");
    expect(markdown).toContain("## ⑧ 来源清单");
    expect(markdown).toContain("Apple supplier pressure is easing.");
    expect(markdown).toContain("https://example.com/evidence-1");
    expect(markdown).toContain("tier 2");
    expect(markdown).toContain("Consumer Electronics (基于推断)");
    expect(markdown).not.toMatch(REDLINE_PATTERN);
  });
});

describe("downloadMarkdown", () => {
  it("downloads markdown content through a temporary anchor", () => {
    const click = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    const previousCreateObjectURL = URL.createObjectURL;
    const previousRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:report");
    URL.revokeObjectURL = vi.fn();
    const createElement = vi.spyOn(document, "createElement");
    createElement.mockReturnValue(anchor);
    const appendChild = vi.spyOn(document.body, "appendChild");
    const removeChild = vi.spyOn(document.body, "removeChild");

    downloadMarkdown("AAPL-report.md", "# Report");

    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(anchor.download).toBe("AAPL-report.md");
    expect(anchor.href).toBe("blob:report");
    expect(appendChild).toHaveBeenCalledWith(anchor);
    expect(click).toHaveBeenCalledTimes(1);
    expect(removeChild).toHaveBeenCalledWith(anchor);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:report");

    createElement.mockRestore();
    appendChild.mockRestore();
    removeChild.mockRestore();
    URL.createObjectURL = previousCreateObjectURL;
    URL.revokeObjectURL = previousRevokeObjectURL;
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
