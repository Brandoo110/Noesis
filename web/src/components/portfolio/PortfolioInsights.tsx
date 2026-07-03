import type { EntityNode, Position } from "../../types/api";
import { CorrelationMatrix } from "./CorrelationMatrix";
import { OverlapPanel } from "./OverlapPanel";
import { PortfolioBrief } from "./PortfolioBrief";
import { SharedSuppliers } from "./SharedSuppliers";

interface PortfolioInsightsProps {
  activeRun: {
    entity: EntityNode | null;
    positionId: string | null;
    status: string;
  };
  onAnalyzed: () => void;
  onBriefPositionSelected?: (positionId: string) => void;
  positions: Position[];
  refreshKey: number;
}

export function PortfolioInsights({
  activeRun,
  onAnalyzed,
  onBriefPositionSelected,
  positions,
  refreshKey
}: PortfolioInsightsProps): JSX.Element {
  return (
    <>
      <PortfolioBrief
        activeRun={{
          positionId: activeRun.positionId,
          status: activeRun.status
        }}
        onSelectPosition={onBriefPositionSelected}
        refreshKey={refreshKey}
      />
      <OverlapPanel refreshKey={refreshKey} />
      <SharedSuppliers
        activeRun={{
          entity: activeRun.entity,
          positionId: activeRun.positionId
        }}
        onAnalyzed={onAnalyzed}
        positions={positions}
        refreshKey={refreshKey}
      />
      <CorrelationMatrix refreshKey={refreshKey} />
    </>
  );
}
