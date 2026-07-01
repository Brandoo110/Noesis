import type { EntityNode, Position } from "../../types/api";
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
  positions: Position[];
  refreshKey: number;
}

export function PortfolioInsights({
  activeRun,
  onAnalyzed,
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
    </>
  );
}
