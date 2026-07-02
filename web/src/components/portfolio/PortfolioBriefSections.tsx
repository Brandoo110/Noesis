import type {
  Basis,
  OverlapGroup,
  PortfolioBrief,
  PortfolioRunHealth
} from "../../types/api";

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
      className="run-health"
    >
      <div className="run-health-top">
        <strong>Brief 运行健康</strong>
        <span>{issueCount} issues</span>
      </div>
      <div className="health-bar" aria-hidden="true">
        <i style={{ flexGrow: completedShare }} />
        <i style={{ flexGrow: degradedShare }} />
        <i style={{ flexGrow: failedShare }} />
      </div>
      <div className="brief-stats">
        <span><strong>{health.total_latest_runs}</strong><small>latest runs</small></span>
        <span><strong>{health.degraded_runs}</strong><small>degraded</small></span>
        <span><strong>{health.completed_without_thesis}</strong><small>no thesis</small></span>
      </div>
      {issueCount > 0 ? <RunHealthIssues health={health} /> : null}
    </section>
  );
}

export function PositionSummaries({
  activeRun,
  brief
}: {
  activeRun?: ActiveRun;
  brief: PortfolioBrief;
}): JSX.Element {
  return (
    <section aria-label="持仓一句话" className="brief-lines">
      <h3>持仓一句话</h3>
      {brief.positions.length === 0 ? <p className="empty-note">暂无持仓 Brief</p> : null}
      <ul>
        {brief.positions.map((position) => (
          <li key={position.position_id}>
            <strong>{position.symbol}</strong>
            <span title={positionSummaryLabel(position, activeRun)}>
              {shortBriefSummary(positionSummaryLabel(position, activeRun))}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BriefOverlaps({ overlaps }: { overlaps: OverlapGroup[] }): JSX.Element {
  return (
    <section aria-label="Brief 产业段重叠" className="overlap-list">
      <h3>产业段重叠</h3>
      {overlaps.length === 0 ? <p className="empty-note">暂无产业段重叠</p> : null}
      <ul className="overlap-list">
        {overlaps.map((group) => (
          <li key={group.segment_id}>
            <strong>{group.segment_name}</strong>
            <span>{group.positions.map((position) => position.symbol).join(" / ")}</span>
            <span className={`basis-badge ${group.basis}`}>{basisLabel(group.basis)}</span>
          </li>
        ))}
      </ul>
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
        <li><strong>{health.completed_without_thesis}</strong><span>completed without thesis</span></li>
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

function healthShare(value: number, total: number): number {
  if (total <= 0) {
    return value > 0 ? value : 0;
  }
  return Math.max(value, value > 0 ? 0.2 : 0);
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}
