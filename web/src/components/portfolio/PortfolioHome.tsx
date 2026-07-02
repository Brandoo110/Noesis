import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { createPosition, listPositions } from "../../api/client";
import { AgentOpsDashboard } from "../agentops/AgentOpsDashboard";
import { GraphExplorer } from "../graph/GraphExplorer";
import { usePortfolioRunSeeds } from "../../hooks/use-portfolio-run-seeds";
import { useRun } from "../../hooks/use-run";
import type { EntityNode, Position } from "../../types/api";
import { PortfolioInsights } from "./PortfolioInsights";
import { PortfolioMobileTabbar } from "./PortfolioMobileTabbar";
import { PositionInput, type PositionFormState } from "./PositionInput";
import { PositionList } from "./PositionList";
import { PortfolioTopbar, type PortfolioFilters } from "./PortfolioTopbar";
import { buildInput, matchesKind, matchesResearch, matchesSearch, prefersReducedMotion, toErrorMessage } from "./portfolio-home-utils";

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

      {error ? <p className="alert" role="alert">{error}</p> : null}

      <div className="portfolio-grid">
        <aside className="left-rail" aria-label="持仓控制台" id="positions">
          <PositionInput
            form={form}
            isSaving={isSaving}
            onSubmit={(event) => void handleSubmit(event)}
            setForm={setForm}
          />

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
          <AgentOpsDashboard />
          {!isLoading ? (
            <PortfolioInsights
              activeRun={{
                entity: run.entity,
                positionId: run.positionId,
                status: run.status
              }}
              onAnalyzed={refreshOverlaps}
              positions={insightPositions}
              refreshKey={overlapRefreshKey}
            />
          ) : null}
        </aside>
      </div>
      <PortfolioMobileTabbar />
    </section>
  );
}

interface GraphSeed {
  positionId: string;
  runId: string;
  seedEntity: EntityNode;
}
