import { useEffect, useMemo, useState } from "react";

import { getCorrelationMatrix } from "../../api/client";
import type {
  CorrelationCell,
  CorrelationMatrix as CorrelationMatrixData,
  MatrixAxis
} from "../../types/api";
import { MatrixDialog } from "./MatrixDialog";

interface CorrelationMatrixProps {
  refreshKey?: number;
}

export function CorrelationMatrix({
  refreshKey = 0
}: CorrelationMatrixProps): JSX.Element {
  const [matrix, setMatrix] = useState<CorrelationMatrixData | null>(null);
  const [isMatrixOpen, setIsMatrixOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setError(null);
    void getCorrelationMatrix()
      .then((payload) => {
        if (isMounted) {
          setMatrix(payload);
        }
      })
      .catch((caught: unknown) => {
        if (isMounted) {
          setError(toErrorMessage(caught));
        }
      });
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  const topPairs = useMemo(() => topCorrelationPairs(matrix, 5), [matrix]);
  const hasMatrix = matrix !== null && matrix.positions.length >= 2 && matrix.cells.length > 0;

  return (
    <small
      aria-label="供应链相关性矩阵"
      className="card correlation-card"
      data-testid="correlation-matrix-panel"
    >
      <div className="card-header compact">
        <div>
          <p className="eyebrow">Correlation</p>
          <h2>供应链相关性</h2>
        </div>
        {hasMatrix ? (
          <button
            className="secondary-button small"
            onClick={() => setIsMatrixOpen(true)}
            type="button"
          >
            查看矩阵
          </button>
        ) : null}
      </div>
      <p className="redline-note">
        <strong>仅供参考</strong>
        <span>：共享上游数越高，潜在共同供应链风险越值得关注。</span>
      </p>
      {error ? <span className="compact-alert" role="alert">{error}</span> : null}
      {matrix === null && !error ? <span className="empty-note">加载中...</span> : null}
      {matrix !== null && (matrix.positions.length < 2 || matrix.cells.length === 0) ? (
        <span className="empty-note">持仓不足，暂无相关性</span>
      ) : null}
      {hasMatrix ? (
        <>
          <ul aria-label="共同供应链关注点" className="correlation-pairs">
            {topPairs.map((pair) => (
              <li
                className="correlation-pair"
                key={`${pair.cell.a_position_id}-${pair.cell.b_position_id}`}
              >
                <span className="correlation-pair-main">
                  <strong>{`${positionLabel(pair.left)} / ${positionLabel(pair.right)}`}</strong>
                  <span className="correlation-count-badge">
                    {`${pair.cell.shared_count} 个共享上游`}
                  </span>
                </span>
                <span className="correlation-suppliers">
                  {supplierSummary(pair.cell.shared_suppliers)}
                </span>
              </li>
            ))}
          </ul>
          {isMatrixOpen && matrix ? (
            <MatrixDialog matrix={matrix} onClose={() => setIsMatrixOpen(false)} />
          ) : null}
        </>
      ) : null}
    </small>
  );
}

interface CorrelationPair {
  cell: CorrelationCell;
  left: MatrixAxis;
  right: MatrixAxis;
}

function topCorrelationPairs(
  matrix: CorrelationMatrixData | null,
  limit: number
): CorrelationPair[] {
  if (!matrix) return [];
  const positionsById = new Map(
    matrix.positions.map((position) => [position.position_id, position])
  );
  return matrix.cells
    .map((cell) => {
      const left = positionsById.get(cell.a_position_id);
      const right = positionsById.get(cell.b_position_id);
      return left && right ? { cell, left, right } : null;
    })
    .filter((pair): pair is CorrelationPair => pair !== null)
    .sort(
      (left, right) =>
        right.cell.shared_count - left.cell.shared_count ||
        positionLabel(left.left).localeCompare(positionLabel(right.left))
    )
    .slice(0, limit);
}

function positionLabel(position: MatrixAxis): string {
  return position.symbol && position.symbol.trim().length > 0
    ? position.symbol
    : position.label;
}

function supplierSummary(suppliers: string[]): string {
  const shown = suppliers.slice(0, 3).join("、");
  return suppliers.length > 3 ? `${shown} 等` : shown;
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "相关性矩阵加载失败";
}
