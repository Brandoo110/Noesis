import { useCallback, useEffect, useMemo, useState } from "react";

import { getCorrelationMatrix, getSharedSuppliers } from "../../api/client";
import { useSupplyChainAnalysis } from "../../hooks/use-supply-chain-analysis";
import type {
  Basis,
  CorrelationMatrix as CorrelationMatrixData,
  EntityNode,
  Position,
  SharedPosition,
  SharedSupplierGroup
} from "../../types/api";
import { MatrixDialog } from "./MatrixDialog";

interface SupplyChainCrossProps {
  activeRun: {
    entity: EntityNode | null;
    positionId: string | null;
  };
  onAnalyzed?: () => void;
  positions: Position[];
  refreshKey?: number;
}

export function SupplyChainCross({
  activeRun,
  onAnalyzed,
  positions,
  refreshKey = 0
}: SupplyChainCrossProps): JSX.Element {
  const [groups, setGroups] = useState<SharedSupplierGroup[]>([]);
  const [matrix, setMatrix] = useState<CorrelationMatrixData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMatrixOpen, setIsMatrixOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCrossData = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [nextGroups, nextMatrix] = await Promise.all([
        getSharedSuppliers(),
        getCorrelationMatrix()
      ]);
      setGroups(nextGroups);
      setMatrix(nextMatrix);
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const analysis = useSupplyChainAnalysis({
    activeRun,
    onAnalyzed: async () => {
      await loadCrossData();
      onAnalyzed?.();
    },
    positions
  });

  useEffect(() => {
    void loadCrossData();
  }, [loadCrossData, refreshKey]);

  const rows = useMemo(() => crossRows(groups), [groups]);
  const hasMatrix = matrix !== null && matrix.positions.length >= 2 && matrix.cells.length > 0;

  return (
    <small
      aria-label="供应链交叉"
      className="card portfolio-brief supply-chain-cross"
      data-testid="supply-chain-cross-panel"
    >
      <div className="card-header compact">
        <div>
          <p className="eyebrow">Supply Chain</p>
          <h2>供应链交叉</h2>
        </div>
        <div className="cross-actions">
          <button
            disabled={analysis.isAnalyzing || analysis.seedCount === 0}
            onClick={() => void analysis.analyze()}
            type="button"
          >
            {analysis.isAnalyzing ? "分析中..." : "分析组合供应链"}
          </button>
          <button
            className="secondary-button small"
            disabled={!hasMatrix}
            onClick={() => setIsMatrixOpen(true)}
            type="button"
          >
            查看矩阵
          </button>
        </div>
      </div>
      <p className="redline-note">
        <strong>仅供参考</strong>
        <span>。这些持仓共享同一上游供应商，可关注共同供应链风险。</span>
      </p>
      {isLoading ? <span className="empty-note">加载中...</span> : null}
      {error ? (
        <span className="compact-alert" role="alert">
          <span>{error}</span>
          <button disabled={isLoading} onClick={() => void loadCrossData()} type="button">
            重新加载供应链交叉
          </button>
        </span>
      ) : null}
      {analysis.error ? <span className="compact-alert">{analysis.error}</span> : null}
      {!isLoading && !error && rows.length === 0 ? (
        <span className="empty-note">暂无供应链交叉</span>
      ) : null}
      {!isLoading && !error && rows.length > 0 ? (
        <ul aria-label="供应链交叉列表" className="cross-list">
          {rows.map((row) => (
            <li key={row.id} className="cross-row">
              <strong>{`${positionLabel(row.left)} × ${positionLabel(row.right)}`}</strong>
              <span>{`共享 ${row.supplierName}`}</span>
              <span className={`basis-badge ${row.basis}`}>{basisLabel(row.basis)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {isMatrixOpen && matrix ? (
        <MatrixDialog matrix={matrix} onClose={() => setIsMatrixOpen(false)} />
      ) : null}
    </small>
  );
}

interface CrossRow {
  id: string;
  left: SharedPosition;
  right: SharedPosition;
  supplierName: string;
  basis: Basis;
}

function crossRows(groups: SharedSupplierGroup[]): CrossRow[] {
  return groups.flatMap((group) =>
    group.positions.flatMap((left, index) =>
      group.positions.slice(index + 1).map((right) => ({
        id: `${group.supplier_id}:${left.position_id}:${right.position_id}`,
        left,
        right,
        supplierName: group.supplier_name,
        basis: group.basis
      }))
    )
  );
}

function positionLabel(position: SharedPosition): string {
  return position.symbol && position.symbol.trim().length > 0
    ? position.symbol
    : position.position_id;
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "供应链交叉加载失败";
}
