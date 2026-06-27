import { useEffect } from "react";

import { confirmThesis } from "../../api/client";
import { useEvidenceDrawer } from "../../context/evidence-drawer";
import { useStockDetail } from "../../hooks/use-stock-detail";
import type { ConfirmationInput } from "../../types/api";
import { AttentionNotes } from "./AttentionNotes";
import { ChainMini } from "./ChainMini";
import { IntelStream } from "./IntelStream";
import { PositionRelation } from "./PositionRelation";
import { StatusSummary } from "./StatusSummary";
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
      <StatusSummary detail={stock.detail} errors={stock.errors} />
      <IntelStream
        items={stock.detail.intelItems}
        onEvidenceClick={open}
      />
      <ChainMini edges={stock.detail.neighbors} />
      <PositionRelation path={stock.detail.relevancePath} />
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
