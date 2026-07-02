import type { Dispatch, SetStateAction } from "react";

import type { PositionKind } from "../../types/api";

export interface PortfolioFilters {
  kind: "all" | PositionKind;
  research: "all" | "researched" | "unresearched";
}

interface PortfolioTopbarProps {
  filters: PortfolioFilters;
  isFilterOpen: boolean;
  isReadinessOpen: boolean;
  searchQuery: string;
  setFilters: Dispatch<SetStateAction<PortfolioFilters>>;
  setIsFilterOpen: Dispatch<SetStateAction<boolean>>;
  setIsReadinessOpen: Dispatch<SetStateAction<boolean>>;
  setSearchQuery: Dispatch<SetStateAction<string>>;
}

const EMPTY_FILTERS: PortfolioFilters = {
  kind: "all",
  research: "all"
};

export function PortfolioTopbar({
  filters,
  isFilterOpen,
  isReadinessOpen,
  searchQuery,
  setFilters,
  setIsFilterOpen,
  setIsReadinessOpen,
  setSearchQuery
}: PortfolioTopbarProps): JSX.Element {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <h1 id="portfolio-title">Noesis Portfolio</h1>
        <p>local intelligence workspace</p>
      </div>
      <label className="topbar-search">
        <span className="sr-only">搜索</span>
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          aria-label="全局搜索"
          placeholder="搜索标的、主题、证据或 thesis..."
          onChange={(event) => setSearchQuery(event.target.value)}
          type="search"
          value={searchQuery}
        />
      </label>
      <div className="topbar-actions" aria-label="工作台工具">
        <button
          aria-expanded={isFilterOpen}
          aria-label="筛选"
          onClick={() => {
            setIsFilterOpen((current) => !current);
            setIsReadinessOpen(false);
          }}
          type="button"
          className="secondary-button"
        >
          <span>Filter</span>
        </button>
        <button
          aria-expanded={isReadinessOpen}
          aria-label="产品状态"
          onClick={() => {
            setIsReadinessOpen((current) => !current);
            setIsFilterOpen(false);
          }}
          type="button"
          className="secondary-button health-button"
        >
          <i aria-hidden="true" />
          <span>Health</span>
        </button>
      </div>
      {isFilterOpen ? (
        <section aria-label="筛选面板" className="popover filter-popover">
          <label>
            持仓类型
            <select
              aria-label="持仓类型筛选"
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  kind: event.target.value as PortfolioFilters["kind"]
                }))
              }
              value={filters.kind}
            >
              <option value="all">全部</option>
              <option value="owned">owned</option>
              <option value="watching">watching</option>
            </select>
          </label>
          <label>
            研究状态
            <select
              aria-label="研究状态筛选"
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  research: event.target.value as PortfolioFilters["research"]
                }))
              }
              value={filters.research}
            >
              <option value="all">全部</option>
              <option value="researched">已研究</option>
              <option value="unresearched">未研究</option>
            </select>
          </label>
          <button onClick={() => setFilters(EMPTY_FILTERS)} type="button">
            重置筛选
          </button>
        </section>
      ) : null}
      {isReadinessOpen ? (
        <section aria-label="产品状态面板" className="popover health-popover">
          <p className="eyebrow">Launch readiness</p>
          <h2>产品状态</h2>
          <ul>
            <li className="health-row"><strong>本地优先</strong><span>SQLite + 本地 Web，无交易通道。</span></li>
            <li className="health-row"><strong>非荐股</strong><span>只输出研究关注点和证据化情报。</span></li>
            <li className="health-row"><strong>证据化</strong><span>结论保留 evidence / source tier / basis 标记。</span></li>
            <li className="health-row"><strong>门禁</strong><span>前端测试和 production build 作为上线检查。</span></li>
          </ul>
        </section>
      ) : null}
    </header>
  );
}
