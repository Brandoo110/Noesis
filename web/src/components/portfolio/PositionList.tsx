import type { EntityNode, Position } from "../../types/api";

export interface PositionListProps {
  activePositionId: string | null;
  emptyMessage?: string;
  onDeletePosition: (positionId: string) => void;
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
  onDeletePosition,
  onViewGraph,
  onStartRun,
  positions,
  runEntity,
  runId,
  runPositionId,
  runStatus
}: PositionListProps): JSX.Element {
  if (positions.length === 0) {
    return <p className="empty-note position-list-empty">{emptyMessage}</p>;
  }

  return (
    <div>
      <div className="pos-head" aria-hidden="true">
        <span>标的</span>
        <span>状态</span>
        <span>RUN</span>
      </div>
      <ul aria-label="持仓列表">
        {positions.map((position) => {
          const label = primaryPositionLabel(position);
          const currentGraph = graphFromActive(position, activePositionId, runId, runEntity, runPositionId, runStatus);
          const latestGraph = graphFromLatest(position);
          const staleGraph = activePositionId === position.id && runPositionId === position.id && currentGraph === null
            ? latestGraph
            : null;
          const inactiveLatestGraph = activePositionId !== position.id ? latestGraph : null;
          const primaryGraph = currentGraph ?? staleGraph ?? inactiveLatestGraph;
          const action = researchActionLabel(position, activePositionId, runId, runPositionId, runStatus);
          const status = positionStatus(position, activePositionId, runId, runEntity, runPositionId, runStatus);

          return (
            <li
              aria-label={primaryGraph ? `打开图谱 ${label}` : undefined}
              className={activePositionId === position.id ? "pos-row pos-row-active" : "pos-row"}
              key={position.id}
              onClick={() => primaryGraph ? onViewGraph(position.id, primaryGraph.runId, primaryGraph.entity) : undefined}
              onKeyDown={(event) => {
                if (primaryGraph && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  onViewGraph(position.id, primaryGraph.runId, primaryGraph.entity);
                }
              }}
              role={primaryGraph ? "button" : undefined}
              tabIndex={primaryGraph ? 0 : undefined}
            >
              <div className="symbol-cell">
                <span aria-hidden="true">{label.slice(0, 1).toUpperCase()}</span>
                <div>
                  <strong>{label}</strong>
                  <small>{secondaryPositionLabel(position, activePositionId, runEntity, runPositionId)}</small>
                  <small>{`${position.market} · ${position.kind}`}</small>
                </div>
              </div>
              <span aria-label={`研究状态 ${label}`} className={`status-chip ${status.tone}`}>
                <strong>{status.label}</strong>
                {status.rawStatus ? <span className="sr-only">{status.rawStatus}</span> : null}
                {status.runId ? <span className="sr-only mono">{status.runId}</span> : null}
              </span>
              <div className="row-actions row-actions-muted">
                <button
                  aria-label={`${action} ${label}`}
                  className="secondary-button"
                  disabled={action === "研究中"}
                  onClick={(event) => {
                    event.stopPropagation();
                    void onStartRun(position.id);
                  }}
                  type="button"
                >
                  {action}
                </button>
                {currentGraph ? (
                  <GraphActionButton graph={currentGraph} label={label} onViewGraph={onViewGraph} positionId={position.id} text="查看图谱" />
                ) : null}
                {staleGraph ? (
                  <GraphActionButton graph={staleGraph} label={label} onViewGraph={onViewGraph} positionId={position.id} text="查看旧图谱" />
                ) : null}
                {inactiveLatestGraph ? (
                  <GraphActionButton graph={inactiveLatestGraph} label={label} onViewGraph={onViewGraph} positionId={position.id} text="查看图谱" />
                ) : null}
                <button
                  aria-label={`删除持仓 ${label}`}
                  className="danger-button small"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDeletePosition(position.id);
                  }}
                  type="button"
                >
                  删除
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <div className="table-footer">
        <span>{`显示 1-${positions.length} · 共 ${positions.length} 项`}</span>
        <span>非荐股 · 每条结论均挂证据</span>
      </div>
    </div>
  );
}

interface GraphRef {
  entity: EntityNode;
  runId: string;
}

interface GraphActionButtonProps {
  graph: GraphRef;
  label: string;
  onViewGraph: PositionListProps["onViewGraph"];
  positionId: string;
  text: "查看图谱" | "查看旧图谱";
}

function GraphActionButton({ graph, label, onViewGraph, positionId, text }: GraphActionButtonProps): JSX.Element {
  return (
    <button
      aria-label={`${text} ${label}`}
      className="graph-button"
      onClick={(event) => {
        event.stopPropagation();
        onViewGraph(positionId, graph.runId, graph.entity);
      }}
      type="button"
    >
      {text}
    </button>
  );
}

function graphFromActive(position: Position, activePositionId: string | null, currentRunId: string | null, currentRunEntity: EntityNode | null, runPositionId: string | null, runStatus: string): GraphRef | null {
  return activePositionId === position.id &&
    currentRunId !== null &&
    currentRunEntity !== null &&
    runPositionId === position.id &&
    isTerminalGraphStatus(runStatus)
    ? { entity: currentRunEntity, runId: currentRunId }
    : null;
}

function graphFromLatest(position: Position): GraphRef | null {
  return typeof position.latest_run_id === "string" &&
    position.latest_run_entity !== null &&
    position.latest_run_entity !== undefined &&
    isTerminalGraphStatus(position.latest_run_status)
    ? { entity: position.latest_run_entity, runId: position.latest_run_id }
    : null;
}

function primaryPositionLabel(position: Position): string {
  const resolvedSymbol = position.latest_run_entity?.symbol?.trim();
  if (resolvedSymbol) return resolvedSymbol.toUpperCase();
  const symbol = position.symbol.trim();
  if (symbol.length > 0) return symbol.toUpperCase();
  if (position.name) return position.name;
  return "未命名公司";
}

function secondaryPositionLabel(position: Position, activePositionId: string | null, runEntity: EntityNode | null, runPositionId: string | null): string {
  if (position.name) return position.name;
  if (activePositionId === position.id && runPositionId === position.id && runEntity) {
    return runEntity.name;
  }
  if (position.latest_run_entity) {
    return position.latest_run_entity.name;
  }
  if (position.symbol.trim().length === 0) return "未填写代码";
  return "待解析";
}

interface PositionStatus {
  label: "已研究" | "研究中" | "未研究" | "待解析";
  rawStatus: string | null;
  runId: string | null;
  tone: "status-ready" | "status-running" | "status-idle" | "status-pending";
}

function positionStatus(position: Position, activePositionId: string | null, currentRunId: string | null, currentRunEntity: EntityNode | null, runPositionId: string | null, runStatus: string): PositionStatus {
  if (activePositionId === position.id && runPositionId === position.id && currentRunId) {
    return activePositionStatus(runStatus, currentRunId, currentRunEntity);
  }
  if (position.latest_run_status === "running") {
    return { label: "研究中", rawStatus: "running", runId: position.latest_run_id ?? null, tone: "status-running" };
  }
  if (position.latest_run_id && position.latest_run_entity && isTerminalGraphStatus(position.latest_run_status)) {
    return { label: "已研究", rawStatus: position.latest_run_status ?? null, runId: position.latest_run_id, tone: "status-ready" };
  }
  if (position.latest_run_id) {
    return { label: "待解析", rawStatus: position.latest_run_status ?? null, runId: position.latest_run_id, tone: "status-pending" };
  }
  return { label: "未研究", rawStatus: null, runId: null, tone: "status-idle" };
}

function activePositionStatus(runStatus: string, runId: string, runEntity: EntityNode | null): PositionStatus {
  if (runStatus === "running") {
    return { label: "研究中", rawStatus: runStatus, runId, tone: "status-running" };
  }
  if (runEntity && isTerminalGraphStatus(runStatus)) {
    return { label: "已研究", rawStatus: runStatus, runId, tone: "status-ready" };
  }
  return { label: "待解析", rawStatus: runStatus, runId, tone: "status-pending" };
}

function isTerminalGraphStatus(status: string | null | undefined): boolean {
  return status === "awaiting_confirmation" || status === "completed";
}

function researchActionLabel(position: Position, activePositionId: string | null, currentRunId: string | null, runPositionId: string | null, runStatus: string): "开始研究" | "重新研究" | "研究中" {
  if (
    (activePositionId === position.id && runPositionId === position.id && runStatus === "running") ||
    position.latest_run_status === "running"
  ) {
    return "研究中";
  }
  if (
    (activePositionId === position.id && runPositionId === position.id && currentRunId !== null) ||
    typeof position.latest_run_id === "string"
  ) {
    return "重新研究";
  }
  return "开始研究";
}
