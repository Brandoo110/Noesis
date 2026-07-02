import { useCallback, useEffect, useState } from "react";

import { getPortfolioBrief } from "../../api/client";
import {
  downloadMarkdown,
  portfolioBriefToMarkdown
} from "../../lib/markdown";
import type { PortfolioBrief as PortfolioBriefData } from "../../types/api";
import {
  BriefOverlaps,
  PositionSummaries,
  RunHealthSummary
} from "./PortfolioBriefSections";

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
          <div className="brief-stats" aria-label="Brief 指标">
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

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "组合 Brief 加载失败";
}
