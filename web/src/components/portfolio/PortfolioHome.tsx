import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { createPosition, listPositions } from "../../api/client";
import { usePortfolioRunSeeds } from "../../hooks/use-portfolio-run-seeds";
import { useRun } from "../../hooks/use-run";
import type { Position } from "../../types/api";
import { OverlapPanel } from "./OverlapPanel";
import { PortfolioBrief } from "./PortfolioBrief";
import { PortfolioGraphWorkspace } from "./PortfolioGraphWorkspace";
import { PositionInput, type PositionFormState } from "./PositionInput";
import { PositionList } from "./PositionList";
import { PortfolioTopbar, type PortfolioFilters } from "./PortfolioTopbar";
import { SupplyChainCross } from "./SupplyChainCross";
import { buildInput, graphSeedForPosition, matchesKind, matchesResearch, matchesSearch, prefersReducedMotion, toErrorMessage } from "./portfolio-home-utils";
import type { GraphSeed } from "../views/view-types";

const EMPTY_FORM: PositionFormState = { symbol: "", market: "US", name: "", kind: "owned" };
const EMPTY_FILTERS: PortfolioFilters = { kind: "all", research: "all" };

interface PortfolioHomeProps {
  onGraphSeedSelected?: (seed: GraphSeed) => void;
}

export function PortfolioHome({ onGraphSeedSelected }: PortfolioHomeProps): JSX.Element {
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState<PositionFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
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
  const shouldRenderInlineGraph = onGraphSeedSelected === undefined;
  const insightPositions = usePortfolioRunSeeds(positions, {
    entity: run.entity,
    positionId: run.positionId,
    runId: run.runId,
    status: run.status
  });

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
    if (graphSeed === null || !shouldRenderInlineGraph) {
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
  }, [graphSeed, shouldRenderInlineGraph]);

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

  function handleBriefPositionSelected(positionId: string): void {
    const nextSeed = graphSeedForPosition(positions, positionId);
    if (nextSeed === null) {
      return;
    }
    if (shouldRenderInlineGraph) {
      setGraphSeed(nextSeed);
    }
    onGraphSeedSelected?.(nextSeed);
  }

  return (
    <section aria-labelledby="portfolio-title" className={shouldRenderInlineGraph ? "page-body" : "portfolio-home"}>
      {shouldRenderInlineGraph ? (
        <PortfolioTopbar
          filters={filters}
          isFilterOpen={isFilterOpen}
          isReadinessOpen={isReadinessOpen}
          searchQuery={searchQuery}
          setFilters={setFilters}
          setIsFilterOpen={setIsFilterOpen}
          setIsReadinessOpen={setIsReadinessOpen}
          setSearchQuery={setSearchQuery}
        />
      ) : null}

      {error ? <p className="compact-alert" role="alert">{error}</p> : null}

      <div className="home-grid">
        <div className="portfolio-main-stack">
          <section className="card positions-card" aria-label="持仓控制台" id="positions">
            <header className="card-header">
              <div>
                <p className="eyebrow">Portfolio</p>
                <h2>持仓</h2>
              </div>
              <span className="count-pill">{filteredPositions.length} ITEMS</span>
              <button className="primary-button" onClick={() => setIsAddOpen((current) => !current)} type="button">
                + 添加持仓
              </button>
            </header>

            {isAddOpen ? (
              <PositionInput form={form} isSaving={isSaving} onSubmit={(event) => void handleSubmit(event)} setForm={setForm} />
            ) : null}

            {isLoading ? (
              <p className="empty-note">加载中...</p>
            ) : positionsError ? (
              <div className="compact-alert" role="alert">
                <span>{positionsError}</span>
                <button onClick={() => void refreshPositions()} type="button">重新加载持仓</button>
              </div>
            ) : (
              <PositionList
                activePositionId={activePositionId}
                onViewGraph={(positionId, runId, seedEntity) => {
                  const nextSeed = { positionId, runId, seedEntity };
                  if (shouldRenderInlineGraph) {
                    setGraphSeed(nextSeed);
                  }
                  onGraphSeedSelected?.(nextSeed);
                }}
                onStartRun={handleStartRun}
                emptyMessage={positions.length === 0 ? "暂无持仓" : "没有匹配的持仓"}
                positions={filteredPositions} runEntity={run.entity} runId={run.runId}
                runPositionId={run.positionId}
                runStatus={run.status}
              />
            )}
          </section>

          {!isLoading ? (
            <section aria-label="组合中央洞察" className="central-insight-grid">
              <OverlapPanel refreshKey={overlapRefreshKey} />
              <SupplyChainCross
                activeRun={{ entity: run.entity, positionId: run.positionId }}
                onAnalyzed={refreshOverlaps}
                positions={insightPositions}
                refreshKey={overlapRefreshKey}
              />
            </section>
          ) : null}
        </div>

        {shouldRenderInlineGraph ? (
          <PortfolioGraphWorkspace graphSeed={graphSeed} onRetryResearch={handleStartRun} onThesisConfirmed={handleThesisConfirmed} workspaceRef={workspaceRef} />
        ) : null}

        <aside className="side-stack" aria-label="组合洞察">
          {!isLoading ? (
            <PortfolioBrief
              activeRun={{ positionId: run.positionId, status: run.status }}
              onSelectPosition={handleBriefPositionSelected}
              refreshKey={overlapRefreshKey}
            />
          ) : null}
        </aside>
      </div>
    </section>
  );
}
