import { useEffect, useMemo, useState } from "react";

import type {
  CorrelationCell,
  CorrelationMatrix as CorrelationMatrixData
} from "../../types/api";
import { CorrelationMatrixTable } from "./CorrelationMatrixTable";

interface MatrixDialogProps {
  matrix: CorrelationMatrixData;
  onClose: () => void;
}

type MatrixMode = "focused" | "all";
type MatrixSize = "standard" | "wide" | "full";

const TOP_CELL_LIMIT = 5;
const FOCUSED_POSITION_LIMIT = 8;

export function MatrixDialog({ matrix, onClose }: MatrixDialogProps): JSX.Element {
  const [mode, setMode] = useState<MatrixMode>("focused");
  const [size, setSize] = useState<MatrixSize>("wide");
  const [selectedCell, setSelectedCell] = useState<CorrelationCell | null>(null);

  const focusedMatrix = useMemo(() => focusMatrix(matrix), [matrix]);
  const displayMatrix = mode === "focused" ? focusedMatrix : matrix;
  const maxCount = useMemo(
    () => Math.max(1, ...(displayMatrix.cells.map((cell) => cell.shared_count) ?? [0])),
    [displayMatrix]
  );

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    setSelectedCell(null);
  }, [mode]);

  return (
    <div className="matrix-layer">
      <button
        aria-label="关闭相关性矩阵遮罩"
        className="drawer-backdrop"
        onClick={onClose}
        type="button"
      />
      <aside
        aria-label="供应链相关性矩阵"
        aria-modal="true"
        className={matrixPanelClass(size)}
        role="dialog"
      >
        <header className="drawer-header matrix-header">
          <div>
            <p className="eyebrow">CORRELATION MATRIX</p>
            <h2>供应链相关性矩阵</h2>
          </div>
          <div className="matrix-header-actions">
            <span aria-label="矩阵宽度" className="matrix-size-controls">
              {(["standard", "wide", "full"] as const).map((nextSize) => (
                <button
                  aria-pressed={size === nextSize}
                  className={sizeButtonClass(size === nextSize)}
                  key={nextSize}
                  onClick={() => setSize(nextSize)}
                  type="button"
                >
                  {sizeLabel(nextSize)}
                </button>
              ))}
            </span>
            <button aria-label="关闭" onClick={onClose} type="button">
              ×
            </button>
          </div>
        </header>
        <div className="matrix-mode-bar">
          <span>
            {mode === "focused"
              ? `重点视图：显示 ${displayMatrix.positions.length} / ${matrix.positions.length} 个持仓`
              : `全部视图：显示 ${matrix.positions.length} 个持仓`}
          </span>
          <button
            className="secondary-button small"
            onClick={() => setMode(mode === "focused" ? "all" : "focused")}
            type="button"
          >
            {mode === "focused" ? "显示全部持仓" : "只看重点关系"}
          </button>
        </div>
        <CorrelationMatrixTable
          matrix={displayMatrix}
          maxCount={maxCount}
          onSelectCell={setSelectedCell}
        />
        {selectedCell ? (
          <span className="correlation-detail" role="status">
            <strong>共享上游</strong>
            <ul>
              {selectedCell.shared_suppliers.map((supplier) => (
                <li key={supplier}>{supplier}</li>
              ))}
            </ul>
          </span>
        ) : (
          <span className="empty-note">点击格子查看共享上游。</span>
        )}
      </aside>
    </div>
  );
}

function focusMatrix(matrix: CorrelationMatrixData): CorrelationMatrixData {
  const focusedCells = [...matrix.cells]
    .filter((cell) => cell.shared_count > 0)
    .sort(compareCells)
    .slice(0, TOP_CELL_LIMIT);
  const selectedIds = new Set<string>();
  for (const cell of focusedCells) {
    selectedIds.add(cell.a_position_id);
    selectedIds.add(cell.b_position_id);
    if (selectedIds.size >= FOCUSED_POSITION_LIMIT) {
      break;
    }
  }
  if (selectedIds.size === 0) {
    return { positions: [], cells: [] };
  }
  const positions = matrix.positions.filter((position) => selectedIds.has(position.position_id));
  const allowedIds = new Set(positions.map((position) => position.position_id));
  return {
    positions,
    cells: focusedCells.filter(
      (cell) => allowedIds.has(cell.a_position_id) && allowedIds.has(cell.b_position_id)
    )
  };
}

function compareCells(left: CorrelationCell, right: CorrelationCell): number {
  return (
    right.shared_count - left.shared_count ||
    left.a_position_id.localeCompare(right.a_position_id) ||
    left.b_position_id.localeCompare(right.b_position_id)
  );
}

function matrixPanelClass(size: MatrixSize): string {
  return `matrix-panel matrix-panel-${size}`;
}

function sizeButtonClass(isActive: boolean): string {
  return isActive ? "matrix-size-button active" : "matrix-size-button";
}

function sizeLabel(size: MatrixSize): string {
  if (size === "standard") return "标准";
  if (size === "full") return "全屏";
  return "宽屏";
}
