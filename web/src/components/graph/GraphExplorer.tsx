import { useEffect, useState } from "react";

import { useExpand } from "../../hooks/use-expand";
import { useEvidenceDrawer } from "../../context/evidence-drawer";
import type { Basis, EntityNode, Relation } from "../../types/api";
import { GraphStage } from "./GraphStage";
import { StockDetail } from "../stock/StockDetail";

export interface GraphExplorerProps {
  onThesisConfirmed?: () => void;
  onRetryResearch?: (positionId: string) => Promise<void>;
  positionId: string;
  runId?: string;
  seedEntity: EntityNode;
}

export function GraphExplorer({
  onThesisConfirmed,
  onRetryResearch,
  positionId,
  runId,
  seedEntity
}: GraphExplorerProps): JSX.Element {
  const evidenceDrawer = useEvidenceDrawer();
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [basisFilter, setBasisFilter] = useState<"all" | Basis>("all");
  const [relationFilter, setRelationFilter] = useState<"all" | Relation>("all");
  const [focusedEntityId, setFocusedEntityId] = useState<string | null>(null);
  const graph = useExpand({
    onViewDetail: runId ? () => setIsDetailOpen(true) : undefined,
    positionId,
    seedEntity
  });

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setIsDetailOpen(false);
      }
    }
    if (!isDetailOpen) return undefined;
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isDetailOpen]);

  function handleRefresh(): void {
    graph.reset();
    setBasisFilter("all");
    setRelationFilter("all");
    setFocusedEntityId(null);
    setIsDetailOpen(false);
  }

  function handleNodeExpand(entityId: string): void {
    void graph.expand(entityId);
  }

  return (
    <section aria-label="图谱探索器" className="graph-card">
      <header className="graph-header">
        <div>
          <p className="eyebrow">RESEARCH GRAPH · LAZY EXPAND</p>
          <h2>{`Research Graph — ${seedEntity.symbol ?? seedEntity.name}`}</h2>
          <p className="empty-note">
            {[seedEntity.symbol, seedEntity.name].filter(Boolean).join(" · ")} · 按需调研：点击节点角标研究一跳关键关系
          </p>
        </div>
        <div className="graph-controls">
          <div aria-label="basis 筛选" className="segmented" role="group">
            {(["all", "source_backed", "inferred"] as const).map((basis) => (
              <button
                aria-pressed={basisFilter === basis}
                key={basis}
                onClick={() => setBasisFilter(basis)}
                type="button"
              >
                {basis === "all" ? "全部" : basis}
              </button>
            ))}
          </div>
          {runId ? (
            <button
              className="primary-button"
              onClick={() => setIsDetailOpen(true)}
              type="button"
            >
              个股详情
            </button>
          ) : null}
          <button className="secondary-button" onClick={handleRefresh} type="button">
            重置图谱
          </button>
        </div>
      </header>
      {graph.notice ? (
        <div className={`graph-status-note ${graph.notice.tone}`}>
          {graph.notice.message}
        </div>
      ) : null}
      <div className="graph-legend" aria-label="图谱图例">
        <span><i className="legend-line source" />source_backed</span>
        <span><i className="legend-line inferred" />inferred</span>
        <span><i className="legend-node seed" />持仓（种子）</span>
        <span><i className="legend-node company" />公司</span>
        <span><i className="legend-node segment" />产业 / 主题</span>
        <strong>lazy expand · {runId ?? "no run"}</strong>
      </div>
      <GraphStage
        basisFilter={basisFilter}
        edges={graph.edges}
        focusedEntityId={focusedEntityId}
        nodes={graph.nodes}
        onClearFocus={() => setFocusedEntityId(null)}
        onExpandNode={handleNodeExpand}
        onFocusNode={setFocusedEntityId}
        onOpenEvidence={evidenceDrawer.open}
        onRelationFilterChange={setRelationFilter}
        onSeedDetail={runId ? () => setIsDetailOpen(true) : undefined}
        relationFilter={relationFilter}
        seedEntity={seedEntity}
      />
      {isDetailOpen && runId ? (
        <div className="detail-layer">
          <button
            aria-label="关闭个股详情遮罩"
            className="drawer-backdrop"
            onClick={() => setIsDetailOpen(false)}
            type="button"
          />
          <StockDetail
            entityId={seedEntity.id}
            onClose={() => setIsDetailOpen(false)}
            onConfirmed={onThesisConfirmed}
            onRetryResearch={
              onRetryResearch ? () => onRetryResearch(positionId) : undefined
            }
            positionId={positionId}
            runId={runId}
          />
        </div>
      ) : null}
    </section>
  );
}
