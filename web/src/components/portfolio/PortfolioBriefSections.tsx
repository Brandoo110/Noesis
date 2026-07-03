import type {
  PortfolioBrief,
  PortfolioRunHealth
} from "../../types/api";
import { useState } from "react";

interface ActiveRun {
  positionId: string | null;
  status: string;
}

export function RunHealthSummary({
  health
}: {
  health: PortfolioRunHealth;
}): JSX.Element {
  const issueCount = health.failed + health.completed_without_thesis + health.degraded_runs;
  const completedShare = healthShare(health.completed, health.total_latest_runs);
  const degradedShare = healthShare(health.degraded_runs, health.total_latest_runs);
  const failedShare = healthShare(health.failed, health.total_latest_runs);
  return (
    <section
      aria-label="Brief 运行健康"
      className={issueCount > 0 ? "run-health run-health-alert" : "run-health"}
    >
      <div className="run-health-top">
        <strong>运行健康</strong>
        <span>{issueCount > 0 ? `异常 ${issueCount}` : "正常"}</span>
      </div>
      <div className="health-bar" aria-hidden="true">
        <i style={{ flexGrow: completedShare }} />
        <i style={{ flexGrow: degradedShare }} />
        <i style={{ flexGrow: failedShare }} />
      </div>
      {issueCount > 0 ? <RunHealthIssues health={health} /> : null}
    </section>
  );
}

export function PositionSummaries({
  activeRun,
  brief,
  onSelectPosition
}: {
  activeRun?: ActiveRun;
  brief: PortfolioBrief;
  onSelectPosition?: (positionId: string) => void;
}): JSX.Element {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const researchedPositions = brief.positions.filter(
    (position) => position.thesis_summary !== null
  );
  const unresearchedCount = brief.positions.length - researchedPositions.length;
  return (
    <section aria-label="持仓一句话" className="brief-lines">
      <h3>持仓一句话</h3>
      {brief.positions.length === 0 ? <p className="empty-note">暂无持仓 Brief</p> : null}
      {brief.positions.length > 0 && researchedPositions.length === 0 ? (
        <p className="empty-note">暂无已研究持仓一句话</p>
      ) : null}
      <ul>
        {researchedPositions.map((position) => {
          const label = positionSummaryLabel(position, activeRun);
          const isLong = label.length > 168;
          const isExpanded = expandedIds.has(position.position_id);
          return (
            <li className="brief-line-item" key={position.position_id}>
              <button
                className="brief-symbol-button"
                onClick={() => onSelectPosition?.(position.position_id)}
                type="button"
              >
                {position.symbol}
              </button>
              <span
                className={isExpanded ? "brief-summary expanded" : "brief-summary"}
                title={label}
              >
                {isExpanded ? label : shortBriefSummary(label)}
              </span>
              {isLong ? (
                <button
                  className="brief-expand-button"
                  aria-label={`${isExpanded ? "收起" : "展开"} ${position.symbol} 摘要`}
                  onClick={() => toggleExpanded(position.position_id, setExpandedIds)}
                  type="button"
                >
                  {isExpanded ? "收起" : "展开"}
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
      {unresearchedCount > 0 ? (
        <p className="brief-unresearched-note">{`${unresearchedCount} 个持仓尚未研究`}</p>
      ) : null}
    </section>
  );
}

function RunHealthIssues({ health }: { health: PortfolioRunHealth }): JSX.Element {
  return (
    <ul>
      {health.failed_runs.map((run) => (
        <li key={run.run_id}>
          <strong>{run.symbol || run.position_id}</strong>
          <span>{run.reason ? `failed: ${run.reason}` : "failed"}</span>
        </li>
      ))}
      {health.completed_without_thesis > 0 ? (
        <li><strong>{health.completed_without_thesis}</strong><span>完成但无 thesis</span></li>
      ) : null}
      {health.degraded_reasons.map((item) => (
        <li key={item.reason}><strong>{item.count}</strong><span>{item.reason}</span></li>
      ))}
    </ul>
  );
}

type BriefPosition = PortfolioBrief["positions"][number];

function positionSummaryLabel(position: BriefPosition, activeRun?: ActiveRun): string {
  if (position.thesis_summary) {
    return position.thesis_summary;
  }
  if (position.thesis_status === "draft") {
    return "待确认 thesis";
  }
  if (activeRun?.positionId === position.position_id) {
    if (activeRun.status === "running") {
      return "研究中";
    }
    if (activeRun.status === "awaiting_confirmation" || activeRun.status === "completed") {
      return "待确认 thesis";
    }
  }
  return "尚未研究";
}

function shortBriefSummary(summary: string): string {
  return summary.length <= 168 ? summary : `${summary.slice(0, 165).trimEnd()}...`;
}

function toggleExpanded(
  positionId: string,
  setExpandedIds: (updater: (current: Set<string>) => Set<string>) => void
): void {
  setExpandedIds((current) => {
    const next = new Set(current);
    if (next.has(positionId)) {
      next.delete(positionId);
    } else {
      next.add(positionId);
    }
    return next;
  });
}

function healthShare(value: number, total: number): number {
  if (total <= 0) {
    return value > 0 ? value : 0;
  }
  return Math.max(value, value > 0 ? 0.2 : 0);
}
