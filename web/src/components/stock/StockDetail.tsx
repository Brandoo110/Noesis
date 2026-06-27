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
  runId: string;
  positionId: string;
}

export function StockDetail({
  entityId,
  onConfirmed,
  runId,
  positionId
}: StockDetailProps): JSX.Element {
  const stock = useStockDetail(entityId, runId, positionId);
  const { open, remember } = useEvidenceDrawer();
  const [showReport, setShowReport] = useState(false);

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

  if (stock.isLoading) {
    return <section aria-label="个股详情">加载中...</section>;
  }

  return (
    <section aria-label="个股详情">
      <button onClick={() => setShowReport((current) => !current)} type="button">
        {showReport ? "隐藏报告" : "查看报告"}
      </button>
      {showReport ? (
        <StockReport detail={stock.detail} onEvidenceClick={open} />
      ) : null}
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
      <ThesisPanel
        onConfirm={(status) => void handleConfirm(status)}
        onEvidenceClick={open}
        thesis={stock.detail.thesis}
      />
      <AttentionNotes
        onEvidenceClick={open}
        thesis={stock.detail.thesis}
      />
    </section>
  );
}
