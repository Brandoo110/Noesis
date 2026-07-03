import { useCallback, useEffect, useState } from "react";

import { getPortfolioBrief } from "../../api/client";
import {
  downloadMarkdown,
  portfolioBriefToMarkdown
} from "../../lib/markdown";
import type { PortfolioBrief as PortfolioBriefData } from "../../types/api";
import {
  PositionSummaries,
  RunHealthSummary
} from "./PortfolioBriefSections";

interface PortfolioBriefProps {
  activeRun?: {
    positionId: string | null;
    status: string;
  };
  onSelectPosition?: (positionId: string) => void;
  refreshKey?: number;
}

export function PortfolioBrief({
  activeRun,
  onSelectPosition,
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
    <section aria-label="组合 Brief" className="card portfolio-brief" id="portfolio-brief">
      <header className="card-header compact">
        <div>
          <p className="eyebrow">Portfolio brief</p>
          <h2>Portfolio Brief</h2>
        </div>
        <button
          className="secondary-button small"
          disabled={!brief}
          onClick={handleExport}
          type="button"
        >
          导出 Markdown
        </button>
      </header>
      <p className="redline-note">
        <strong>仅供参考</strong>
        <span>。用于研究跟踪，保留产业段重叠和推断标记。</span>
      </p>
      {exportedFilename ? (
        <p className="toast" role="status">
          已生成 {exportedFilename}，内容沿用当前 Brief 与红线措辞。
        </p>
      ) : null}
      {isLoading ? <p className="empty-note">加载中...</p> : null}
      {error ? (
        <div className="compact-alert" role="alert">
          <span>{error}</span>
          <button disabled={isLoading} onClick={() => void loadBrief()} type="button">
            重新加载 Brief
          </button>
        </div>
      ) : null}
      {!isLoading && !error && brief ? (
        <>
          <div
            aria-label="Brief 指标"
            className={
              issueCount(brief) > 0
                ? "brief-stats brief-stats-alert"
                : "brief-stats"
            }
          >
            <span>
              <strong>{brief.positions.length}</strong>
              <small>持仓</small>
            </span>
            <span>
              <strong>{confirmedCount(brief)}</strong>
              <small>thesis</small>
            </span>
            <span>
              <strong>{brief.overlaps.length}</strong>
              <small>重叠</small>
            </span>
            <span>
              <strong>{issueCount(brief)}</strong>
              <small>异常</small>
            </span>
          </div>
          <RunHealthSummary health={brief.run_health} />
          <PositionSummaries
            activeRun={activeRun}
            brief={brief}
            onSelectPosition={onSelectPosition}
          />
        </>
      ) : null}
    </section>
  );
}

function confirmedCount(brief: PortfolioBriefData): number {
  return brief.positions.filter((position) => position.thesis_summary).length;
}

function issueCount(brief: PortfolioBriefData): number {
  return (
    brief.run_health.failed +
    brief.run_health.completed_without_thesis +
    brief.run_health.degraded_runs
  );
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "组合 Brief 加载失败";
}
