import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { EvidenceDrawer } from "../evidence/EvidenceDrawer";
import { EvidenceDrawerProvider } from "../../context/evidence-drawer";
import {
  makeEdge,
  makeEntity,
  makeEvidence,
  makeOverlapGroup,
  makeRunDetail
} from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { UseStockDetailResult } from "../../hooks/use-stock-detail";
import { useStockDetail } from "../../hooks/use-stock-detail";
import type { StockDetailData } from "../../hooks/use-stock-detail";
import { StockDetail } from "./StockDetail";

vi.mock("../../hooks/use-stock-detail", () => ({
  useStockDetail: vi.fn()
}));

vi.mock("../../api/client", () => ({
  confirmThesis: vi.fn(),
  getEvidence: vi.fn()
}));

const useStockDetailMock = vi.mocked(useStockDetail);
const confirmThesisMock = vi.mocked(client.confirmThesis);
const getEvidenceMock = vi.mocked(client.getEvidence);

describe("StockDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders stock detail sections with global evidence entry points", async () => {
    useStockDetailMock.mockReturnValue(makeHookResult());

    render(
      <EvidenceDrawerProvider>
        <StockDetail entityId="entity-aapl" positionId="position-1" runId="run-1" />
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    expect(screen.getByRole("heading", { name: "现状一句话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "分类情报流" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "产业链位置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "和持仓关系" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "和其他持仓的关系" })
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Thesis" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "关注点" })).toBeInTheDocument();

    const intel = screen.getByLabelText("情报 Supplier update");
    expect(within(intel).getByText("neutral")).toBeInTheDocument();
    expect(within(intel).getByText("tier 2")).toBeInTheDocument();
    fireEvent.click(within(intel).getByRole("button", { name: "查看证据" }));
    const drawer = await screen.findByRole("dialog", { name: "证据抽屉" });
    expect(drawer).toBeInTheDocument();
    expect(within(drawer).getByText("Supplier update")).toBeInTheDocument();
    expect(getEvidenceMock).not.toHaveBeenCalled();

    expect(screen.getByText("供应商")).toBeInTheDocument();
    expect(screen.getByText("Apple Inc. / TSMC")).toBeInTheDocument();
    expect(screen.getByText("Consumer Electronics")).toBeInTheDocument();
    expect(screen.getByText("MSFT")).toBeInTheDocument();
    expect(screen.getByText("持有理由")).toBeInTheDocument();
    expect(screen.getByText("关键假设")).toBeInTheDocument();
    expect(screen.getByText("风险")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("组合重叠关系")).getByText("仅供参考")
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("关注点列表")).getByText("仅供参考")
    ).toBeInTheDocument();
  });

  it("opens evidence drawer from thesis and attention notes", async () => {
    useStockDetailMock.mockReturnValue(makeHookResult());

    render(
      <EvidenceDrawerProvider>
        <StockDetail entityId="entity-aapl" positionId="position-1" runId="run-1" />
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(
      within(screen.getByLabelText("关键假设")).getByRole("button", {
        name: "查看证据"
      })
    );
    expect(
      await screen.findByRole("dialog", { name: "证据抽屉" })
    ).toBeInTheDocument();

    fireEvent.click(
      within(screen.getByLabelText("关注点列表")).getByRole("button", {
        name: "查看证据"
      })
    );
    await waitFor(() =>
      expect(
        within(screen.getByRole("dialog", { name: "证据抽屉" })).getByText(
          "Supplier update"
        )
      ).toBeInTheDocument()
    );
  });

  it("confirms thesis assumptions and refreshes detail", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    const onConfirmed = vi.fn();
    useStockDetailMock.mockReturnValue(makeHookResult({ refresh }));
    confirmThesisMock.mockResolvedValue({
      run_id: "run-1",
      status: "completed",
      thesis_id: "thesis-1"
    });

    render(
      <EvidenceDrawerProvider>
        <StockDetail
          entityId="entity-aapl"
          onConfirmed={onConfirmed}
          positionId="position-1"
          runId="run-1"
        />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "确认 thesis 假设" }));

    expect(confirmThesisMock).toHaveBeenCalledWith("thesis-1", {
      status: "confirmed"
    });
    await vi.waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(onConfirmed).toHaveBeenCalledTimes(1);
  });

  it("keeps investment-related wording only as small attention notes", () => {
    useStockDetailMock.mockReturnValue(makeHookResult());

    render(
      <EvidenceDrawerProvider>
        <StockDetail entityId="entity-aapl" positionId="position-1" runId="run-1" />
      </EvidenceDrawerProvider>
    );

    expect(screen.queryByText(REDLINE_PATTERN)).not.toBeInTheDocument();
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
  const entity = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const evidence = { ...makeEvidence(), title: "Supplier update" };
  const run = makeRunDetail(entity, evidence);
  const tsm = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
  return {
    entityId: "entity-aapl",
    positionId: "position-1",
    runId: "run-1",
    run,
    entity,
    evidences: run.evidences,
    intelItems: run.intel_items,
    thesis: run.thesis,
    neighbors: [makeEdge("edge-1", tsm, "source_backed", ["evidence-1"])],
    overlaps: [makeOverlapGroup()],
    relevancePath: [entity, tsm]
  };
}
