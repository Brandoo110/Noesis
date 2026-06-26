import { confirmThesis } from "../../api/client";
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
  runId: string;
  positionId: string;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

export function StockDetail({
  entityId,
  runId,
  positionId,
  onEvidenceClick
}: StockDetailProps): JSX.Element {
  const stock = useStockDetail(entityId, runId, positionId);

  async function handleConfirm(status: ConfirmationInput["status"]): Promise<void> {
    if (!stock.detail.thesis) {
      return;
    }
    await confirmThesis(stock.detail.thesis.id, { status });
    await stock.refresh();
  }

  if (stock.isLoading) {
    return <section aria-label="个股详情">加载中...</section>;
  }

  return (
    <section aria-label="个股详情">
      <StatusSummary detail={stock.detail} errors={stock.errors} />
      <IntelStream
        items={stock.detail.intelItems}
        onEvidenceClick={onEvidenceClick}
      />
      <ChainMini edges={stock.detail.neighbors} />
      <PositionRelation path={stock.detail.relevancePath} />
      <ThesisPanel
        onConfirm={(status) => void handleConfirm(status)}
        onEvidenceClick={onEvidenceClick}
        thesis={stock.detail.thesis}
      />
      <AttentionNotes
        onEvidenceClick={onEvidenceClick}
        thesis={stock.detail.thesis}
      />
    </section>
  );
}
