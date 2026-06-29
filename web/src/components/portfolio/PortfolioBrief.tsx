import { useCallback, useEffect, useState } from "react";

import { getPortfolioBrief } from "../../api/client";
import {
  downloadMarkdown,
  portfolioBriefToMarkdown
} from "../../lib/markdown";
import type {
  Basis,
  OverlapGroup,
  PortfolioBrief as PortfolioBriefData,
  PortfolioRunHealth
} from "../../types/api";

interface PortfolioBriefProps {
  activeRun?: {
    positionId: string | null;
    status: string;
  };
  refreshKey?: number;
}

export function PortfolioBrief({
  activeRun,
  refreshKey = 0
}: PortfolioBriefProps): JSX.Element {
  const [brief, setBrief] = useState<PortfolioBriefData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportedFilename, setExportedFilename] = useState<string | null>(null);

  const loadBrief = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      setBrief(await getPortfolioBrief());
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBrief();
  }, [loadBrief, refreshKey]);

  function handleExport(): void {
    if (brief) {
      const filename = "portfolio-brief.md";
      downloadMarkdown(filename, portfolioBriefToMarkdown(brief));
      setExportedFilename(filename);
    }
  }

  return (
    <section aria-label="组合 Brief" className="surface brief-surface" id="portfolio-brief">
      <header className="section-heading">
        <div>
          <p className="eyebrow">Portfolio brief</p>
          <h2>Portfolio Brief</h2>
        </div>
        <button
          className="primary-action"
          disabled={!brief}
          onClick={handleExport}
          type="button"
        >
          导出 Markdown
        </button>
      </header>
      <p className="muted">
        <strong>仅供参考</strong>
        <span>。用于研究跟踪，保留产业段重叠和推断标记。</span>
      </p>
      {exportedFilename ? (
        <p className="export-notice" role="status">
          已生成 {exportedFilename}，内容沿用当前 Brief 与红线措辞。
        </p>
      ) : null}
      {isLoading ? <p className="muted">加载中...</p> : null}
      {error ? (
        <div className="inline-recovery" role="alert">
          <span>{error}</span>
          <button disabled={isLoading} onClick={() => void loadBrief()} type="button">
            重新加载 Brief
          </button>
        </div>
      ) : null}
      {!isLoading && !error && brief ? (
        <>
          <div className="brief-metrics" aria-label="Brief 指标">
            <span>
              <strong>{brief.positions.length}</strong>
              <small>持仓数量</small>
            </span>
            <span>
              <strong>{brief.overlaps.length}</strong>
              <small>重叠主题</small>
            </span>
            <span>
              <strong>{confirmedCount(brief)}</strong>
              <small>thesis ready</small>
            </span>
          </div>
          <RunHealthSummary health={brief.run_health} />
          <PositionSummaries activeRun={activeRun} brief={brief} />
          <BriefOverlaps overlaps={brief.overlaps} />
        </>
      ) : null}
    </section>
  );
}

function confirmedCount(brief: PortfolioBriefData): number {
  return brief.positions.filter((position) => position.thesis_summary).length;
}

function RunHealthSummary({
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
      className={issueCount > 0 ? "brief-health brief-health-alert" : "brief-health"}
    >
      <span className="brief-health-title">Run Health Status</span>
      <div className="brief-health-bar" aria-hidden="true">
        <span className="brief-health-bar-complete" style={{ flexGrow: completedShare }} />
        <span className="brief-health-bar-degraded" style={{ flexGrow: degradedShare }} />
        <span className="brief-health-bar-failed" style={{ flexGrow: failedShare }} />
      </div>
      <div className="brief-health-metrics">
        <span>
          <strong>{health.total_latest_runs}</strong>
          <small>latest runs</small>
        </span>
        <span>
          <strong>{health.degraded_runs}</strong>
          <small>degraded</small>
        </span>
        <span>
          <strong>{health.completed_without_thesis}</strong>
          <small>no thesis</small>
        </span>
      </div>
      {issueCount > 0 ? <RunHealthIssues health={health} /> : null}
    </section>
  );
}

function healthShare(value: number, total: number): number {
  if (total <= 0) {
    return value > 0 ? value : 0;
  }
  return Math.max(value, value > 0 ? 0.2 : 0);
}

function RunHealthIssues({ health }: { health: PortfolioRunHealth }): JSX.Element {
  return (
    <ul className="brief-health-issues">
      {health.failed_runs.map((run) => (
        <li key={run.run_id}>
          <strong>{run.symbol || run.position_id}</strong>
          <span>{run.reason ? `failed: ${run.reason}` : "failed"}</span>
        </li>
      ))}
      {health.completed_without_thesis > 0 ? (
        <li>
          <strong>{health.completed_without_thesis}</strong>
          <span>completed without thesis</span>
        </li>
      ) : null}
      {health.degraded_reasons.map((item) => (
        <li key={item.reason}>
          <strong>{item.count}</strong>
          <span>{item.reason}</span>
        </li>
      ))}
    </ul>
  );
}

function PositionSummaries({
  activeRun,
  brief
}: {
  activeRun?: PortfolioBriefProps["activeRun"];
  brief: PortfolioBriefData;
}): JSX.Element {
  return (
    <section aria-label="持仓一句话" className="brief-block">
      <h3>持仓一句话</h3>
      {brief.positions.length === 0 ? <p className="empty-note">暂无持仓 Brief</p> : null}
      <ul className="summary-list">
        {brief.positions.map((position) => (
          <li key={position.position_id}>
            <strong>{position.symbol}</strong>
            <BriefSummaryText summary={positionSummaryLabel(position, activeRun)} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function BriefSummaryText({ summary }: { summary: string }): JSX.Element {
  return <span title={summary}>{shortBriefSummary(summary)}</span>;
}

type BriefPosition = PortfolioBriefData["positions"][number];

function positionSummaryLabel(
  position: BriefPosition,
  activeRun: PortfolioBriefProps["activeRun"]
): string {
  if (position.thesis_summary) {
    return position.thesis_summary;
  }
  if (position.thesis_status === "draft") {
    return "待确认 thesis";
  }
  if (
    activeRun?.positionId === position.position_id &&
    (activeRun.status === "awaiting_confirmation" || activeRun.status === "completed")
  ) {
    return "待确认 thesis";
  }
  if (activeRun?.positionId === position.position_id && activeRun.status === "running") {
    return "研究中";
  }
  return "尚未研究";
}

function shortBriefSummary(summary: string): string {
  const maxLength = 168;
  if (summary.length <= maxLength) {
    return summary;
  }
  return `${summary.slice(0, maxLength - 3).trimEnd()}...`;
}

function BriefOverlaps({
  overlaps
}: {
  overlaps: OverlapGroup[];
}): JSX.Element {
  return (
    <section aria-label="Brief 产业段重叠" className="brief-block">
      <h3>产业段重叠</h3>
      {overlaps.length === 0 ? <p className="empty-note">暂无产业段重叠</p> : null}
      <ul className="overlap-list">
        {overlaps.map((group) => (
          <li key={group.segment_id}>
            <strong>{group.segment_name}</strong>
            <span>{group.positions.map((position) => position.symbol).join(" / ")}</span>
            <span className={basisClassName(group.basis)}>
              {basisLabel(group.basis)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}

function basisClassName(basis: Basis): string {
  return basis === "source_backed" ? "brief-source-backed" : "brief-inferred";
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "组合 Brief 加载失败";
}
