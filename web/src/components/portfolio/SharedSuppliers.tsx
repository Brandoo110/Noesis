import { useCallback, useEffect, useState } from "react";

import { getSharedSuppliers } from "../../api/client";
import { useSupplyChainAnalysis } from "../../hooks/use-supply-chain-analysis";
import type { Basis, EntityNode, Position, SharedSupplierGroup } from "../../types/api";

interface SharedSuppliersProps {
  activeRun: {
    entity: EntityNode | null;
    positionId: string | null;
  };
  onAnalyzed?: () => void;
  positions: Position[];
  refreshKey?: number;
}

export function SharedSuppliers({
  activeRun,
  onAnalyzed,
  positions,
  refreshKey = 0
}: SharedSuppliersProps): JSX.Element {
  const [groups, setGroups] = useState<SharedSupplierGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSharedSuppliers = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      setGroups(await getSharedSuppliers());
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const analysis = useSupplyChainAnalysis({
    activeRun,
    onAnalyzed: async () => {
      await loadSharedSuppliers();
      onAnalyzed?.();
    },
    positions
  });

  useEffect(() => {
    void loadSharedSuppliers();
  }, [loadSharedSuppliers, refreshKey]);

  return (
    <small
      aria-label="共享供应商提示"
      className="card portfolio-brief"
      data-testid="shared-suppliers-panel"
    >
      <div className="card-header compact">
        <div>
          <p className="eyebrow">Supply Chain</p>
          <h2>共享上游供应商</h2>
        </div>
        <button
          disabled={analysis.isAnalyzing || analysis.seedCount === 0}
          onClick={() => void analysis.analyze()}
          type="button"
        >
          {analysis.isAnalyzing ? "分析中..." : "分析组合供应链"}
        </button>
      </div>
      <p className="muted">
        <strong>仅供参考</strong>
        <span>。这些持仓共享同一上游供应商，可关注共同供应链风险。</span>
      </p>
      {isLoading ? <span className="empty-note">加载中...</span> : null}
      {error ? (
        <span className="compact-alert" role="alert">
          <span>{error}</span>
          <button disabled={isLoading} onClick={() => void loadSharedSuppliers()} type="button">
            重新加载共享供应商
          </button>
        </span>
      ) : null}
      {analysis.error ? <span className="compact-alert">{analysis.error}</span> : null}
      {!isLoading && !error && groups.length === 0 ? (
        <span className="empty-note">暂无共享上游供应商</span>
      ) : null}
      {!isLoading && !error && groups.length > 0 ? (
        <ul aria-label="共享上游供应商列表" className="overlap-list">
          {groups.map((group) => (
            <li key={group.supplier_id}>
              <strong>{group.supplier_name}</strong>
              <span>{group.positions.map(positionLabel).join(" / ")}</span>
              <span className={`basis-badge ${group.basis}`}>
                {basisLabel(group.basis)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </small>
  );
}

function positionLabel(position: SharedSupplierGroup["positions"][number]): string {
  return position.symbol && position.symbol.trim().length > 0
    ? position.symbol
    : position.position_id;
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "共享供应商加载失败";
}
