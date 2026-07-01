import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { getCorrelationMatrix } from "../../api/client";
import type {
  CorrelationCell,
  CorrelationMatrix as CorrelationMatrixData,
  MatrixAxis
} from "../../types/api";

interface CorrelationMatrixProps {
  refreshKey?: number;
}

export function CorrelationMatrix({
  refreshKey = 0
}: CorrelationMatrixProps): JSX.Element {
  const [matrix, setMatrix] = useState<CorrelationMatrixData | null>(null);
  const [selectedCell, setSelectedCell] = useState<CorrelationCell | null>(null);
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

  const maxCount = useMemo(
    () => Math.max(1, ...(matrix?.cells.map((cell) => cell.shared_count) ?? [0])),
    [matrix]
  );

  return (
    <small
      aria-label="供应链相关性矩阵"
      className="surface overlap-surface correlation-matrix-surface"
      data-testid="correlation-matrix-panel"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Correlation</p>
          <h2>供应链相关性</h2>
        </div>
      </div>
      <p className="muted">
        <strong>仅供参考</strong>
        <span>：共享上游数越高，潜在共同供应链风险越值得关注。</span>
      </p>
      {error ? <span className="inline-recovery" role="alert">{error}</span> : null}
      {matrix === null && !error ? <span className="muted">加载中...</span> : null}
      {matrix !== null && (matrix.positions.length < 2 || matrix.cells.length === 0) ? (
        <span className="empty-note">持仓不足，暂无相关性</span>
      ) : null}
      {matrix !== null && matrix.positions.length >= 2 && matrix.cells.length > 0 ? (
        <>
          <table className="correlation-matrix-table">
            <thead>
              <tr>
                <th aria-label="持仓" />
                {matrix.positions.map((position) => (
                  <th key={position.position_id}>{positionLabel(position)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.positions.map((row) => (
                <tr key={row.position_id}>
                  <th>{positionLabel(row)}</th>
                  {matrix.positions.map((column) =>
                    matrixCell(row, column, matrix.cells, maxCount, setSelectedCell)
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {selectedCell ? (
            <span className="correlation-detail" role="status">
              <strong>共享上游</strong>
              <ul>
                {selectedCell.shared_suppliers.map((supplier) => (
                  <li key={supplier}>{supplier}</li>
                ))}
              </ul>
            </span>
          ) : null}
        </>
      ) : null}
    </small>
  );
}

function matrixCell(
  row: MatrixAxis,
  column: MatrixAxis,
  cells: CorrelationCell[],
  maxCount: number,
  setSelectedCell: (cell: CorrelationCell) => void
): JSX.Element {
  const testId = `correlation-cell-${row.position_id}-${column.position_id}`;
  if (row.position_id === column.position_id) {
    return <td data-testid={testId} key={column.position_id} />;
  }
  const cell = findCell(row.position_id, column.position_id, cells);
  if (!cell) {
    return <td data-testid={testId} key={column.position_id} />;
  }
  return (
    <td data-testid={testId} key={column.position_id}>
      <button
        className="correlation-cell"
        onClick={() => setSelectedCell(cell)}
        onMouseEnter={() => setSelectedCell(cell)}
        style={neutralCellStyle(cell.shared_count, maxCount)}
        type="button"
      >
        {cell.shared_count}
      </button>
    </td>
  );
}

function findCell(
  leftPositionId: string,
  rightPositionId: string,
  cells: CorrelationCell[]
): CorrelationCell | undefined {
  return cells.find(
    (cell) =>
      (cell.a_position_id === leftPositionId && cell.b_position_id === rightPositionId) ||
      (cell.a_position_id === rightPositionId && cell.b_position_id === leftPositionId)
  );
}

function neutralCellStyle(count: number, maxCount: number): CSSProperties {
  const alpha = (0.16 + (count / maxCount) * 0.44).toFixed(2);
  return { backgroundColor: `rgba(76, 84, 92, ${alpha})` };
}

function positionLabel(position: MatrixAxis): string {
  return position.symbol && position.symbol.trim().length > 0
    ? position.symbol
    : position.label;
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "相关性矩阵加载失败";
}
