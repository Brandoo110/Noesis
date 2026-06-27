import type { EntityNode, Position } from "../../types/api";

export interface PositionListProps {
  activePositionId: string | null;
  onViewGraph: (positionId: string, seedEntity: EntityNode) => void;
  onStartRun: (positionId: string) => Promise<void>;
  positions: Position[];
  runEntity: EntityNode | null;
  runId: string | null;
  runStatus: string;
}

export function PositionList({
  activePositionId,
  onViewGraph,
  onStartRun,
  positions,
  runEntity,
  runId,
  runStatus
}: PositionListProps): JSX.Element {
  if (positions.length === 0) {
    return <p>暂无持仓</p>;
  }

  return (
    <ul aria-label="持仓列表">
      {positions.map((position) => (
        <li key={position.id}>
          <strong>{position.symbol}</strong>
          <span>{position.name ?? "未命名"}</span>
          <span>{position.market}</span>
          <span>{position.kind}</span>
          <button
            aria-label={`开始研究 ${position.symbol}`}
            onClick={() => void onStartRun(position.id)}
            type="button"
          >
            开始研究
          </button>
          {activePositionId === position.id ? (
            <span aria-label={`研究状态 ${position.symbol}`}>
              <span>{runStatus}</span>
              {runId ? <span>{runId}</span> : null}
              {canViewGraph(runStatus, runEntity) ? (
                <button
                  aria-label={`查看图谱 ${position.symbol}`}
                  onClick={() => onViewGraph(position.id, runEntity)}
                  type="button"
                >
                  查看图谱
                </button>
              ) : null}
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function canViewGraph(
  runStatus: string,
  runEntity: EntityNode | null
): runEntity is EntityNode {
  return (
    runEntity !== null &&
    (runStatus === "awaiting_confirmation" || runStatus === "completed")
  );
}
