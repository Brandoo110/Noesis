import type { CSSProperties } from "react";

import type { CorrelationCell, CorrelationMatrix, MatrixAxis } from "../../types/api";

interface CorrelationMatrixTableProps {
  matrix: CorrelationMatrix;
  maxCount: number;
  onSelectCell: (cell: CorrelationCell) => void;
}

export function CorrelationMatrixTable({
  matrix,
  maxCount,
  onSelectCell
}: CorrelationMatrixTableProps): JSX.Element {
  return (
    <div className="matrix-scroll" data-testid="correlation-matrix-scroll">
      <table
        aria-label="供应链相关性"
        className="matrix"
        data-axis-count={matrix.positions.length}
      >
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
                matrixCell(row, column, matrix.cells, maxCount, onSelectCell)
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
