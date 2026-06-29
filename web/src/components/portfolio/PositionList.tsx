import type { EntityNode, Position } from "../../types/api";

export interface PositionListProps {
  activePositionId: string | null;
  emptyMessage?: string;
  onViewGraph: (positionId: string, runId: string, seedEntity: EntityNode) => void;
  onStartRun: (positionId: string) => Promise<void>;
  positions: Position[];
  runEntity: EntityNode | null;
  runId: string | null;
  runPositionId: string | null;
  runStatus: string;
}

export function PositionList({
  activePositionId,
  emptyMessage = "暂无持仓",
  onViewGraph,
  onStartRun,
  positions,
  runEntity,
  runId,
  runPositionId,
  runStatus
}: PositionListProps): JSX.Element {
  if (positions.length === 0) {
    return <p className="empty-note">{emptyMessage}</p>;
  }

  return (
    <div className="position-table-shell">
      <div className="position-table-header" aria-hidden="true">
        <span>标的</span>
        <span>市场/类型</span>
        <span>RUN</span>
      </div>
      <ul aria-label="持仓列表" className="position-list">
        {positions.map((position) => {
          const positionLabel = primaryPositionLabel(position);
          const currentRunId = runId;
          const currentRunEntity = runEntity;
          const latestRunId = position.latest_run_id;
          const latestRunEntity = position.latest_run_entity;
          const currentGraph =
            activePositionId === position.id &&
            currentRunId !== null &&
            currentRunEntity !== null &&
            runPositionId === position.id &&
            isTerminalGraphStatus(runStatus)
              ? { entity: currentRunEntity, runId: currentRunId }
              : null;
          const latestGraph =
            typeof latestRunId === "string" &&
            latestRunEntity !== null &&
            latestRunEntity !== undefined &&
            isTerminalGraphStatus(position.latest_run_status)
              ? { entity: latestRunEntity, runId: latestRunId }
              : null;
          const staleGraph =
            activePositionId === position.id &&
            runPositionId === position.id &&
            currentGraph === null
              ? latestGraph
              : null;
          const inactiveLatestGraph =
            activePositionId !== position.id ? latestGraph : null;
          const action = researchActionLabel(
            position,
            activePositionId,
            currentRunId,
            runPositionId,
            runStatus
          );

          return (
            <li
              className={
                activePositionId === position.id
                  ? "position-row position-row-active"
                  : "position-row"
              }
              key={position.id}
            >
              <div className="position-main">
                <span className="position-icon" aria-hidden="true">
                  {positionLabel.slice(0, 1).toUpperCase()}
                </span>
                <span>
                  <strong>{positionLabel}</strong>
                  <span>
                    {secondaryPositionLabel(position, activePositionId, runEntity, runPositionId)}
                  </span>
                </span>
              </div>
              <div className="position-meta">
                <span>{position.market}</span>
                <span>{position.kind}</span>
              </div>
              <div className="position-actions">
                <button
                  aria-label={`${action} ${positionLabel}`}
                  disabled={action === "研究中"}
                  onClick={() => void onStartRun(position.id)}
                  type="button"
                >
                  {action}
                </button>
                {activePositionId === position.id ? (
                  <span
                    aria-label={`研究状态 ${positionLabel}`}
                    className="run-status"
                  >
                    <span className="status-chip">{statusLabel(runStatus)}</span>
                    <span className="raw-status">{runStatus}</span>
                    {currentRunId ? <span className="run-id">{currentRunId}</span> : null}
                    {currentGraph ? (
                      <button
                        aria-label={`查看图谱 ${positionLabel}`}
                        className="secondary-action"
                        onClick={() =>
                          onViewGraph(position.id, currentGraph.runId, currentGraph.entity)
                        }
                        type="button"
                      >
                        查看图谱
                      </button>
                    ) : null}
                    {staleGraph ? (
                      <button
                        aria-label={`查看旧图谱 ${positionLabel}`}
                        className="secondary-action"
                        onClick={() =>
                          onViewGraph(position.id, staleGraph.runId, staleGraph.entity)
                        }
                        type="button"
                      >
                        查看旧图谱
                      </button>
                    ) : null}
                  </span>
                ) : null}
                {inactiveLatestGraph ? (
                  <button
                    aria-label={`查看图谱 ${positionLabel}`}
                    className="secondary-action"
                    onClick={() =>
                      onViewGraph(position.id, inactiveLatestGraph.runId, inactiveLatestGraph.entity)
                    }
                    type="button"
                  >
                    查看图谱
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
      <div className="position-table-footer">
        <span>{`显示 1-${positions.length} / ${positions.length}`}</span>
        <span aria-hidden="true">‹ ›</span>
      </div>
    </div>
  );
}

function primaryPositionLabel(position: Position): string {
  const symbol = position.symbol.trim();
  if (symbol.length > 0) {
    return symbol.toUpperCase();
  }
  if (position.name) {
    return position.name;
  }
  return "未命名公司";
}

function secondaryPositionLabel(
  position: Position,
  activePositionId: string | null,
  runEntity: EntityNode | null,
  runPositionId: string | null
): string {
  if (position.symbol.trim().length === 0 && position.name) {
    return "未填写代码";
  }
  if (position.name) {
    return position.name;
  }
  if (activePositionId === position.id && runPositionId === position.id && runEntity) {
    return runEntity.name;
  }
  return "待解析";
}

function statusLabel(status: string): string {
  if (status === "awaiting_confirmation") {
    return "待确认";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "running") {
    return "研究中";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
}

function isTerminalGraphStatus(status: string | null | undefined): boolean {
  return status === "awaiting_confirmation" || status === "completed";
}

function researchActionLabel(
  position: Position,
  activePositionId: string | null,
  currentRunId: string | null,
  runPositionId: string | null,
  runStatus: string,
): "开始研究" | "重新研究" | "研究中" {
  if (
    (activePositionId === position.id &&
      runPositionId === position.id &&
      runStatus === "running") ||
    position.latest_run_status === "running"
  ) {
    return "研究中";
  }
  if (
    (activePositionId === position.id &&
      runPositionId === position.id &&
      currentRunId !== null) ||
    typeof position.latest_run_id === "string"
  ) {
    return "重新研究";
  }
  return "开始研究";
}
