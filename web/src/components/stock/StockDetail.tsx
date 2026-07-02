import { useEffect, useState } from "react";

import { confirmThesis } from "../../api/client";
import { useEvidenceDrawer } from "../../context/evidence-drawer";
import { useStockDetail } from "../../hooks/use-stock-detail";
import type { ConfirmationInput } from "../../types/api";
import { AttentionNotes } from "./AttentionNotes";
import { ChainMini } from "./ChainMini";
import { IntelStream } from "./IntelStream";
import { PortfolioOverlap } from "./PortfolioOverlap";
import { PositionRelation } from "./PositionRelation";
import { StatusSummary } from "./StatusSummary";
import { StockReport } from "./StockReport";
import { ThesisPanel } from "./ThesisPanel";

export interface StockDetailProps {
  entityId: string;
  onConfirmed?: () => void;
  onRetryResearch?: () => Promise<void>;
  runId: string;
  positionId: string;
}

export function StockDetail({
  entityId,
  onConfirmed,
  onRetryResearch,
  runId,
  positionId
}: StockDetailProps): JSX.Element {
  const stock = useStockDetail(entityId, runId, positionId);
  const { open, remember } = useEvidenceDrawer();
  const [showReport, setShowReport] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    remember(stock.detail.evidences);
  }, [remember, stock.detail.evidences]);

  async function handleConfirm(status: ConfirmationInput["status"]): Promise<void> {
    if (!stock.detail.thesis) {
      return;
    }
    await confirmThesis(stock.detail.thesis.id, { status });
    await stock.refresh();
    onConfirmed?.();
  }

  async function handleRetryResearch(): Promise<void> {
    if (!onRetryResearch) {
      return;
    }
    setIsRetrying(true);
    try {
      await onRetryResearch();
    } finally {
      setIsRetrying(false);
    }
  }

  if (stock.isLoading) {
    return <section aria-label="个股详情" className="detail-panel">加载中...</section>;
  }

  const hasMissingCompletedThesis =
    stock.detail.run?.status === "completed" && stock.detail.thesis === null;

  return (
    <section aria-label="个股详情" className="detail-panel">
      <header className="drawer-header">
        <div>
          <p className="eyebrow">Stock detail / Thesis view</p>
          <h2>
            {stock.detail.entity?.symbol ?? stock.detail.entityId}
            <span>{stock.detail.entity?.name ? ` · ${stock.detail.entity.name}` : ""}</span>
          </h2>
          <div className="detail-chips">
            <span>{stock.detail.entity?.market ?? "market unknown"}</span>
            <span>{`run id: ${runId}`}</span>
            <span>{stock.detail.run?.status ?? "status unknown"}</span>
            <span>{`evidence ${stock.detail.evidences.length}`}</span>
          </div>
        </div>
        <button
          className="secondary-button"
          onClick={() => setShowReport((current) => !current)}
          type="button"
        >
          {showReport ? "隐藏报告" : "查看报告"}
        </button>
      </header>
      {hasMissingCompletedThesis ? (
        <section className="degraded-banner" role="status">
          <div>
            <strong>本次研究已完成，但没有生成 thesis</strong>
            <p>
              证据和分类情报仍可查看；上线使用时可重新研究，直到生成可确认的 thesis。
            </p>
          </div>
          {onRetryResearch ? (
            <button
              className="secondary-button"
              disabled={isRetrying}
              onClick={() => void handleRetryResearch()}
              type="button"
            >
              {isRetrying ? "重新研究中" : "重新研究"}
            </button>
          ) : null}
        </section>
      ) : null}
      {showReport ? (
        <div className="summary-card">
          <StockReport detail={stock.detail} onEvidenceClick={open} />
        </div>
      ) : null}
      <div>
        <div>
          <StatusSummary detail={stock.detail} errors={stock.errors} />
          <IntelStream
            items={stock.detail.intelItems}
            onEvidenceClick={open}
          />
          <ChainMini edges={stock.detail.neighbors} />
          <PositionRelation path={stock.detail.relevancePath} />
          <PortfolioOverlap
            entityId={entityId}
            overlaps={stock.detail.overlaps}
          />
        </div>
        <aside>
          <ThesisPanel
            onConfirm={(status) => void handleConfirm(status)}
            onEvidenceClick={open}
            thesis={stock.detail.thesis}
          />
          <AttentionNotes
            onEvidenceClick={open}
            thesis={stock.detail.thesis}
          />
        </aside>
      </div>
    </section>
  );
}
