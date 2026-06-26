import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import type { UseStockDetailResult } from "../../hooks/use-stock-detail";
import { useStockDetail } from "../../hooks/use-stock-detail";
import type { StockDetailData } from "../../hooks/use-stock-detail";
import { StockDetail } from "./StockDetail";

vi.mock("../../hooks/use-stock-detail", () => ({
  useStockDetail: vi.fn()
}));

vi.mock("../../api/client", () => ({
  confirmThesis: vi.fn()
}));

const useStockDetailMock = vi.mocked(useStockDetail);
const confirmThesisMock = vi.mocked(client.confirmThesis);

describe("StockDetail", () => {
  it("renders stock detail sections with evidence entry points", () => {
    const onEvidenceClick = vi.fn();
    useStockDetailMock.mockReturnValue(makeHookResult());

    render(
      <StockDetail
        entityId="entity-aapl"
        onEvidenceClick={onEvidenceClick}
        positionId="position-1"
        runId="run-1"
      />
    );

    expect(screen.getByRole("heading", { name: "现状一句话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "分类情报流" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "产业链位置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "和持仓关系" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Thesis" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "关注点" })).toBeInTheDocument();

    const intel = screen.getByLabelText("情报 Supplier update");
    expect(within(intel).getByText("neutral")).toBeInTheDocument();
    expect(within(intel).getByText("tier 2")).toBeInTheDocument();
    fireEvent.click(within(intel).getByRole("button", { name: "查看证据" }));
    expect(onEvidenceClick).toHaveBeenCalledWith(["evidence-1"]);

    expect(screen.getByText("供应商")).toBeInTheDocument();
    expect(screen.getByText("Apple Inc. / TSMC")).toBeInTheDocument();
    expect(screen.getByText("持有理由")).toBeInTheDocument();
    expect(screen.getByText("关键假设")).toBeInTheDocument();
    expect(screen.getByText("风险")).toBeInTheDocument();
    expect(screen.getByText("仅供参考")).toBeInTheDocument();
  });

  it("confirms thesis assumptions and refreshes detail", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    useStockDetailMock.mockReturnValue(makeHookResult({ refresh }));
    confirmThesisMock.mockResolvedValue({
      run_id: "run-1",
      status: "completed",
      thesis_id: "thesis-1"
    });

    render(
      <StockDetail entityId="entity-aapl" positionId="position-1" runId="run-1" />
    );

    fireEvent.click(screen.getByRole("button", { name: "确认 thesis 假设" }));

    expect(confirmThesisMock).toHaveBeenCalledWith("thesis-1", {
      status: "confirmed"
    });
    await vi.waitFor(() => expect(refresh).toHaveBeenCalled());
  });

  it("keeps investment-related wording only as small attention notes", () => {
    useStockDetailMock.mockReturnValue(makeHookResult());

    render(
      <StockDetail entityId="entity-aapl" positionId="position-1" runId="run-1" />
    );

    expect(
      screen.queryByText(/买入|卖出|加仓|减仓|目标价|股价预测|target price/i)
    ).not.toBeInTheDocument();
    const attention = screen.getByLabelText("关注点列表");
    expect(attention.tagName.toLowerCase()).toBe("small");
    expect(within(attention).getByText(/仅供参考/)).toBeInTheDocument();
  });
});

function makeHookResult(
  overrides: Partial<UseStockDetailResult> = {}
): UseStockDetailResult {
  return {
    detail: makeDetail(),
    errors: {},
    isLoading: false,
    refresh: vi.fn(),
    ...overrides
  };
}

function makeDetail(): StockDetailData {
  return {
    entityId: "entity-aapl",
    positionId: "position-1",
    runId: "run-1",
    run: null,
    entity: {
      id: "entity-aapl",
      name: "Apple Inc.",
      node_type: "company",
      symbol: "AAPL",
      market: "US"
    },
    evidences: [
      {
        id: "evidence-1",
        source: "web",
        source_tier: 2,
        url: "https://example.com",
        title: "Supplier update",
        snippet: "Supplier pressure eased.",
        captured_at: "2026-06-27T00:00:00Z",
        published_at: null
      }
    ],
    intelItems: [
      {
        title: "Supplier update",
        content: "Supplier pressure eased.",
        event_type: "supply_chain",
        source: "web",
        source_tier: 2,
        url: "https://example.com",
        published_at: null,
        sentiment: { dir: "neutral", conf: 0.7 },
        evidence_ids: ["evidence-1"]
      }
    ],
    thesis: {
      id: "thesis-1",
      summary: "Apple supplier pressure is easing.",
      status: "draft",
      assumptions: [
        {
          text: "Supplier pressure supports current thesis.",
          kind: "reason",
          evidence_ids: ["evidence-1"]
        },
        {
          text: "Supplier pressure remains observable.",
          kind: "assumption",
          evidence_ids: ["evidence-1"]
        },
        {
          text: "Supplier pressure could reverse.",
          kind: "risk",
          evidence_ids: ["evidence-1"]
        }
      ]
    },
    neighbors: [
      {
        id: "edge-1",
        to_entity_id: "entity-tsm",
        to_name: "TSMC",
        to_symbol: "TSM",
        relation: "supplier",
        basis: "source_backed",
        confidence: 0.82,
        evidence_ids: ["evidence-1"],
        source_tier: 2,
        rationale: "Supplier relation is source-backed.",
        neighbor: {
          id: "entity-tsm",
          name: "TSMC",
          node_type: "company",
          symbol: "TSM",
          market: "US"
        }
      }
    ],
    relevancePath: [
      {
        id: "entity-aapl",
        name: "Apple Inc.",
        node_type: "company",
        symbol: "AAPL",
        market: "US"
      },
      {
        id: "entity-tsm",
        name: "TSMC",
        node_type: "company",
        symbol: "TSM",
        market: "US"
      }
    ]
  };
}
