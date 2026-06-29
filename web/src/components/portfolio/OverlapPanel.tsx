import { useCallback, useEffect, useState } from "react";

import { getOverlaps } from "../../api/client";
import type { Basis, OverlapGroup } from "../../types/api";

interface OverlapPanelProps {
  refreshKey?: number;
}

export function OverlapPanel({
  refreshKey = 0
}: OverlapPanelProps): JSX.Element {
  const [groups, setGroups] = useState<OverlapGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverlaps = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      setGroups(await getOverlaps());
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverlaps();
  }, [loadOverlaps, refreshKey]);

  return (
    <small
      aria-label="组合重叠提示"
      className="surface overlap-surface"
      data-testid="overlap-panel"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Overlap</p>
          <h2>产业段重叠</h2>
        </div>
      </div>
      <p className="muted">
        <strong>仅供参考</strong>
        <span>。这些持仓在同一产业段，可关注共同暴露。</span>
      </p>
      {isLoading ? <span className="muted">加载中...</span> : null}
      {error ? (
        <span className="inline-recovery" role="alert">
          <span>{error}</span>
          <button disabled={isLoading} onClick={() => void loadOverlaps()} type="button">
            重新加载重叠
          </button>
        </span>
      ) : null}
      {!isLoading && !error && groups.length === 0 ? (
        <span className="empty-note">暂无产业段重叠</span>
      ) : null}
      {!isLoading && !error && groups.length > 0 ? (
        <ul aria-label="产业段重叠列表" className="overlap-list">
          {groups.map((group) => (
            <li key={group.segment_id}>
              <strong>{group.segment_name}</strong>
              <span>{group.positions.map((position) => position.symbol).join(" / ")}</span>
              <span className={basisClassName(group.basis)}>
                {basisLabel(group.basis)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </small>
  );
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}

function basisClassName(basis: Basis): string {
  return basis === "source_backed" ? "overlap-source-backed" : "overlap-inferred";
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "重叠提示加载失败";
}
