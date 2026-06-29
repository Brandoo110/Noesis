import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { createPosition, listPositions } from "../../api/client";
import { GraphExplorer } from "../graph/GraphExplorer";
import { useRun } from "../../hooks/use-run";
import type {
  CreatePositionInput,
  EntityNode,
  Position,
  PositionKind
} from "../../types/api";
import { OverlapPanel } from "./OverlapPanel";
import { PortfolioBrief } from "./PortfolioBrief";
import { PositionList } from "./PositionList";

interface PositionFormState {
  symbol: string;
  market: string;
  name: string;
  kind: PositionKind;
}

interface PortfolioFilters {
  kind: "all" | PositionKind;
  research: "all" | "researched" | "unresearched";
}

const EMPTY_FORM: PositionFormState = {
  symbol: "",
  market: "US",
  name: "",
  kind: "owned"
};

const EMPTY_FILTERS: PortfolioFilters = {
  kind: "all",
  research: "all"
};

export function PortfolioHome(): JSX.Element {
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState<PositionFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activePositionId, setActivePositionId] = useState<string | null>(null);
  const [graphSeed, setGraphSeed] = useState<GraphSeed | null>(null);
  const [overlapRefreshKey, setOverlapRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<PortfolioFilters>(EMPTY_FILTERS);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isReadinessOpen, setIsReadinessOpen] = useState(false);
  const run = useRun();
  const workspaceRef = useRef<HTMLElement | null>(null);

  const filteredPositions = useMemo(
    () =>
      positions.filter((position) =>
        matchesSearch(position, searchQuery) &&
        matchesKind(position, filters.kind) &&
        matchesResearch(position, filters.research, {
          activeRunId: run.runId,
          activeRunPositionId: run.positionId
        })
      ),
    [filters.kind, filters.research, positions, run.positionId, run.runId, searchQuery]
  );

  const refreshOverlaps = useCallback((): void => {
    setOverlapRefreshKey((current) => current + 1);
  }, []);

  const refreshPositions = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setPositionsError(null);
    try {
      setPositions(await listPositions());
    } catch (caught) {
      setPositionsError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshPositions();
  }, [refreshPositions]);

  useEffect(() => {
    if (graphSeed === null) {
      return;
    }

    const workspace = workspaceRef.current;
    if (!workspace || typeof workspace.scrollIntoView !== "function") {
      return;
    }

    workspace.scrollIntoView({
      block: "start",
      behavior: prefersReducedMotion() ? "auto" : "smooth"
    });
    workspace.focus({ preventScroll: true });
  }, [graphSeed]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const input = buildInput(form);
    if (!input.symbol && !input.name) {
      setError("请输入 Symbol 或公司名称");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await createPosition(input);
      setForm(EMPTY_FORM);
      await refreshPositions();
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleStartRun(positionId: string): Promise<void> {
    setError(null);
    setActivePositionId(positionId);
    try {
      await run.start(positionId);
      refreshOverlaps();
    } catch (caught) {
      setError(toErrorMessage(caught));
    }
  }

  async function handleThesisConfirmed(): Promise<void> {
    setError(null);
    try {
      await run.refresh();
      refreshOverlaps();
    } catch (caught) {
      setError(toErrorMessage(caught));
    }
  }

  return (
    <section aria-labelledby="portfolio-title" className="portfolio-page">
      <header className="app-topbar">
        <div className="brand-lockup">
          <span aria-hidden="true" className="brand-mark">N</span>
          <div>
            <h1 id="portfolio-title">Noesis Portfolio</h1>
            <p>local intelligence workspace</p>
          </div>
        </div>
        <label className="command-search">
          <span>搜索</span>
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
          >
            <span aria-hidden="true" className="tool-glyph">F</span>
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
          >
            <span aria-hidden="true" className="tool-glyph">H</span>
            <span>Health</span>
          </button>
          <span className="user-badge" aria-label="local user">U</span>
        </div>
        {isFilterOpen ? (
          <section aria-label="筛选面板" className="topbar-popover filter-panel">
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
          <section aria-label="产品状态面板" className="topbar-popover readiness-panel">
            <p className="eyebrow">Launch readiness</p>
            <h2>产品状态</h2>
            <ul>
              <li><strong>本地优先</strong><span>SQLite + 本地 Web，无交易通道。</span></li>
              <li><strong>非荐股</strong><span>只输出研究关注点和证据化情报。</span></li>
              <li><strong>证据化</strong><span>结论保留 evidence / source tier / basis 标记。</span></li>
              <li><strong>门禁</strong><span>前端测试和 production build 作为上线检查。</span></li>
            </ul>
          </section>
        ) : null}
      </header>

      {error ? <p className="alert" role="alert">{error}</p> : null}

      <div className="portfolio-grid">
        <aside className="left-rail" aria-label="持仓控制台" id="positions">
          <section className="surface compact-surface">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Position input</p>
                <h2>Position Input</h2>
              </div>
            </div>
            <form
              aria-label="新增持仓表单"
              className="position-form"
              onSubmit={(event) => void handleSubmit(event)}
            >
              <label>
                Symbol
                <input
                  name="symbol"
                  onChange={(event) => setFormField("symbol", event.target.value, setForm)}
                  placeholder="可选：TSLA"
                  value={form.symbol}
                />
              </label>
              <label>
                Market
                <input
                  name="market"
                  onChange={(event) => setFormField("market", event.target.value, setForm)}
                  required
                  value={form.market}
                />
              </label>
              <label>
                Name
                <input
                  name="name"
                  onChange={(event) => setFormField("name", event.target.value, setForm)}
                  placeholder="公司名：SpaceX"
                  value={form.name}
                />
              </label>
              <label>
                Kind
                <select
                  name="kind"
                  onChange={(event) =>
                    setFormField("kind", event.target.value as PositionKind, setForm)
                  }
                  value={form.kind}
                >
                  <option value="owned">owned</option>
                  <option value="watching">watching</option>
                </select>
              </label>
              <button className="primary-action" disabled={isSaving} type="submit">
                新增持仓
              </button>
            </form>
          </section>

          <section className="surface positions-surface">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Portfolio</p>
                <h2>Portfolio</h2>
              </div>
              <span className="count-pill">{filteredPositions.length} ITEMS</span>
            </div>
            {isLoading ? (
              <p className="muted">加载中...</p>
            ) : positionsError ? (
              <div className="inline-recovery" role="alert">
                <span>{positionsError}</span>
                <button onClick={() => void refreshPositions()} type="button">
                  重新加载持仓
                </button>
              </div>
            ) : (
              <PositionList
                activePositionId={activePositionId}
                onViewGraph={(positionId, runId, seedEntity) => {
                  setGraphSeed({ positionId, runId, seedEntity });
                }}
                onStartRun={handleStartRun}
                emptyMessage={positions.length === 0 ? "暂无持仓" : "没有匹配的持仓"}
                positions={filteredPositions}
                runEntity={run.entity}
                runId={run.runId}
                runPositionId={run.positionId}
                runStatus={run.status}
              />
            )}
          </section>
        </aside>

        <section
          aria-label="研究工作区"
          className="workspace-surface"
          id="research-workspace"
          ref={workspaceRef}
          tabIndex={-1}
        >
          {graphSeed ? (
            <GraphExplorer
              onThesisConfirmed={() => void handleThesisConfirmed()}
              onRetryResearch={handleStartRun}
              positionId={graphSeed.positionId}
              runId={graphSeed.runId}
              seedEntity={graphSeed.seedEntity}
            />
          ) : (
            <div className="empty-workspace">
              <p className="eyebrow">图谱探索器</p>
              <h2>选择一个完成研究的持仓查看图谱</h2>
              <p>
                点击“开始研究”，等待 run 进入待确认或完成状态后，打开产业链图谱和个股详情。
              </p>
            </div>
          )}
        </section>

        <aside className="right-rail" aria-label="组合洞察">
          {!isLoading ? (
            <>
              <PortfolioBrief
                activeRun={{
                  positionId: run.positionId,
                  status: run.status
                }}
                refreshKey={overlapRefreshKey}
              />
              <OverlapPanel refreshKey={overlapRefreshKey} />
            </>
          ) : null}
        </aside>
      </div>
      <nav aria-label="移动端导航" className="mobile-tabbar">
        <a href="#portfolio-title">
          <span aria-hidden="true">I</span>
          <strong>Intelligence</strong>
        </a>
        <a aria-current="page" href="#portfolio-title">
          <span aria-hidden="true">P</span>
          <strong>Portfolio</strong>
        </a>
        <a href="#positions">
          <span aria-hidden="true">W</span>
          <strong>Positions</strong>
        </a>
        <a href="#research-workspace">
          <span aria-hidden="true">R</span>
          <strong>Research</strong>
        </a>
        <a href="#portfolio-brief">
          <span aria-hidden="true">A</span>
          <strong>Analytics</strong>
        </a>
      </nav>
    </section>
  );
}

interface GraphSeed {
  positionId: string;
  runId: string;
  seedEntity: EntityNode;
}

function buildInput(form: PositionFormState): CreatePositionInput {
  const symbol = form.symbol.trim();
  const name = form.name.trim();
  return {
    symbol: symbol.length > 0 ? symbol : null,
    market: form.market.trim(),
    name: name.length > 0 ? name : null,
    kind: form.kind
  };
}

function setFormField<Key extends keyof PositionFormState>(
  key: Key,
  value: PositionFormState[Key],
  setForm: React.Dispatch<React.SetStateAction<PositionFormState>>
): void {
  setForm((current) => ({ ...current, [key]: value }));
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "请求失败";
}

function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function matchesSearch(position: Position, searchQuery: string): boolean {
  const query = searchQuery.trim().toLowerCase();
  if (query.length === 0) {
    return true;
  }

  return [position.symbol, position.name, position.market, position.kind]
    .filter(Boolean)
    .some((value) => value?.toLowerCase().includes(query));
}

function matchesKind(position: Position, filter: PortfolioFilters["kind"]): boolean {
  return filter === "all" || position.kind === filter;
}

function matchesResearch(
  position: Position,
  filter: PortfolioFilters["research"],
  activeRun: { activeRunId: string | null; activeRunPositionId: string | null }
): boolean {
  if (filter === "all") {
    return true;
  }

  const hasResearch =
    typeof position.latest_run_id === "string" ||
    (activeRun.activeRunPositionId === position.id && activeRun.activeRunId !== null);
  return filter === "researched" ? hasResearch : !hasResearch;
}
