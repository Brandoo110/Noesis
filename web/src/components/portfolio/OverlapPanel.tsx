import { useEffect, useState } from "react";

import { getOverlaps } from "../../api/client";
import type { Basis, OverlapGroup } from "../../types/api";

export function OverlapPanel(): JSX.Element {
  const [groups, setGroups] = useState<OverlapGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    getOverlaps()
      .then((nextGroups) => {
        if (isMounted) {
          setGroups(nextGroups);
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
  }, []);

  return (
    <small aria-label="组合重叠提示" data-testid="overlap-panel">
      <strong>仅供参考</strong>
      <span>这些持仓在同一产业段，可关注共同暴露。</span>
      {isLoading ? <span>加载中...</span> : null}
      {error ? <span role="alert">{error}</span> : null}
      {!isLoading && !error && groups.length === 0 ? (
        <span>暂无产业段重叠</span>
      ) : null}
      {!isLoading && !error && groups.length > 0 ? (
        <ul aria-label="产业段重叠列表">
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
