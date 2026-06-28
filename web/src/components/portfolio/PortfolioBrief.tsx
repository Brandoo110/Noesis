import { useEffect, useState } from "react";

import { getPortfolioBrief } from "../../api/client";
import {
  downloadMarkdown,
  portfolioBriefToMarkdown
} from "../../lib/markdown";
import type {
  Basis,
  OverlapGroup,
  PortfolioBrief as PortfolioBriefData
} from "../../types/api";

interface PortfolioBriefProps {
  refreshKey?: number;
}

export function PortfolioBrief({
  refreshKey = 0
}: PortfolioBriefProps): JSX.Element {
  const [brief, setBrief] = useState<PortfolioBriefData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    getPortfolioBrief()
      .then((nextBrief) => {
        if (isMounted) {
          setBrief(nextBrief);
        }
      })
      .catch((caught: unknown) => {
        if (isMounted) {
          setError(toErrorMessage(caught));
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  function handleExport(): void {
    if (brief) {
      downloadMarkdown("portfolio-brief.md", portfolioBriefToMarkdown(brief));
    }
  }

  return (
    <section aria-label="组合 Brief">
      <header>
        <h2>组合 Brief</h2>
        <button disabled={!brief} onClick={handleExport} type="button">
          导出 Markdown
        </button>
      </header>
      <small>仅供参考</small>
      <p>用于研究跟踪，保留产业段重叠和推断标记。</p>
      {isLoading ? <p>加载中...</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {!isLoading && !error && brief ? (
        <>
          <PositionSummaries brief={brief} />
          <BriefOverlaps overlaps={brief.overlaps} />
        </>
      ) : null}
    </section>
  );
}

function PositionSummaries({
  brief
}: {
  brief: PortfolioBriefData;
}): JSX.Element {
  return (
    <section aria-label="持仓一句话">
      <h3>持仓一句话</h3>
      {brief.positions.length === 0 ? <p>暂无持仓 Brief</p> : null}
      <ul>
        {brief.positions.map((position) => (
          <li key={position.position_id}>
            <strong>{position.symbol}</strong>
            <span>{position.thesis_summary ?? "尚未研究"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function BriefOverlaps({
  overlaps
}: {
  overlaps: OverlapGroup[];
}): JSX.Element {
  return (
    <section aria-label="Brief 产业段重叠">
      <h3>产业段重叠</h3>
      {overlaps.length === 0 ? <p>暂无产业段重叠</p> : null}
      <ul>
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
