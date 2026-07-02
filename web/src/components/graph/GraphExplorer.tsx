import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  type EdgeTypes,
  type NodeTypes,
  type ReactFlowInstance
} from "reactflow";
import "reactflow/dist/style.css";

import { useExpand } from "../../hooks/use-expand";
import { useEvidenceDrawer } from "../../context/evidence-drawer";
import type { Basis, Edge, EntityNode } from "../../types/api";
import { EdgeView } from "./EdgeView";
import { EntityNodeView } from "./EntityNodeView";
import { StockDetail } from "../stock/StockDetail";

export interface GraphExplorerProps {
  onThesisConfirmed?: () => void;
  onRetryResearch?: (positionId: string) => Promise<void>;
  positionId: string;
  runId?: string;
  seedEntity: EntityNode;
}

const NODE_TYPES: NodeTypes = { entity: EntityNodeView };

const EDGE_TYPES: EdgeTypes = { edge: EdgeView };

const RELATION_LABELS: Record<Edge["relation"], string> = {
  belongs_to: "归属",
  competitor: "竞争对手",
  customer: "客户",
  supplier: "供应商"
};

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
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);
  const graph = useExpand({
    onViewDetail: runId ? () => setIsDetailOpen(true) : undefined,
    positionId,
    seedEntity
  });
  const visibleEdges = basisFilter === "all"
    ? graph.edges
    : graph.edges.filter((edge) => edge.data?.edge.basis === basisFilter);
  const nodeById = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node.data.entity])),
    [graph.nodes]
  );
  const relationRows = useMemo(
    () =>
      visibleEdges
        .map((flowEdge) => {
          const edge = flowEdge.data?.edge;
          if (!edge) {
            return null;
          }
          return {
            edge,
            source: nodeById.get(flowEdge.source),
            target: nodeById.get(flowEdge.target) ?? edge.neighbor
          };
        })
        .filter((row): row is RelationRow => row !== null),
    [nodeById, visibleEdges]
  );

  useEffect(() => {
    if (!flowInstance) {
      return;
    }
    window.requestAnimationFrame(() => {
      flowInstance.fitView({ maxZoom: 0.95, padding: 0.24 });
    });
  }, [flowInstance, graph.nodes.length, visibleEdges.length]);

  function handleFitView(): void {
    flowInstance?.fitView({ maxZoom: 0.95, padding: 0.24 });
  }

  function handleRefresh(): void {
    graph.reset();
    setIsDetailOpen(false);
    window.requestAnimationFrame(() => {
      flowInstance?.fitView({ maxZoom: 0.95, padding: 0.24 });
    });
  }

  return (
    <section aria-label="图谱探索器" className="graph-explorer">
      <header className="graph-header">
        <div>
          <p className="eyebrow">Research Graph</p>
          <h2>{`Research Graph - ${entityLabel(seedEntity)}`}</h2>
          <p className="muted">
            {[seedEntity.symbol, seedEntity.name].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="graph-actions">
          <button onClick={handleFitView} type="button">Fit View</button>
          <label className="graph-filter">
            证据边
            <select
              aria-label="图谱边筛选"
              onChange={(event) => setBasisFilter(event.target.value as "all" | Basis)}
              value={basisFilter}
            >
              <option value="all">全部</option>
              <option value="source_backed">source_backed</option>
              <option value="inferred">inferred</option>
            </select>
          </label>
          <button aria-label="刷新" onClick={handleRefresh} type="button">Focus Mode</button>
        </div>
      </header>
      <div className="graph-toolbar">
        <div className="graph-legend" aria-label="图谱图例">
          <span><i className="legend-line source-backed" />source_backed</span>
          <span><i className="legend-line inferred" />inferred</span>
          <span><i className="legend-dot holding" />持仓（种子）</span>
          <span><i className="legend-dot company" />公司</span>
          <span><i className="legend-dot segment" />产业 / 主题</span>
        </div>
        <div className="graph-run-chip">
          <span>lazy expand</span>
          <strong>{runId ?? "no run"}</strong>
        </div>
      </div>
      <ReactFlowProvider>
        <div className="graph-canvas">
          <ReactFlow
            edgeTypes={EDGE_TYPES}
            edges={visibleEdges}
            fitView
            fitViewOptions={{ maxZoom: 0.95, padding: 0.24 }}
            minZoom={0.25}
            nodeTypes={NODE_TYPES}
            nodes={graph.nodes}
            onInit={setFlowInstance}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>
      </ReactFlowProvider>
      <section aria-label="关系清单" className="relationship-panel">
        <div className="relationship-panel-header">
          <div>
            <p className="eyebrow">Relationship Evidence</p>
            <h3>Active Relationships</h3>
          </div>
          <span className="count-pill">{relationRows.length}</span>
        </div>
        {relationRows.length > 0 ? (
          <>
          <div className="relationship-table-header" aria-hidden="true">
            <span>From → To</span>
            <span>Relation</span>
            <span>Basis</span>
            <span>Conf %</span>
            <span>Evid</span>
            <span>Rationale</span>
          </div>
          <ul className="relationship-list">
            {relationRows.map(({ edge, source, target }) => (
              <li className="relationship-row" key={edge.id}>
                <div className="relationship-route">
                  <strong>{`${entityLabel(source)} → ${entityLabel(target)}`}</strong>
                </div>
                <span className="relationship-relation">{RELATION_LABELS[edge.relation]}</span>
                <span
                  className={
                    edge.basis === "source_backed"
                      ? "source-badge"
                      : "inferred-badge"
                  }
                >
                  {edge.basis === "source_backed" ? "Source" : "Inferred"}
                </span>
                <span className="relationship-confidence">
                  {`${Math.round(edge.confidence * 100)}%`}
                </span>
                <span className="relationship-evidence-cell">
                  <span>{edge.evidence_ids.length}</span>
                  {edge.evidence_ids.length > 0 ? (
                    <button
                      className="secondary-action"
                      onClick={() => evidenceDrawer.open(edge.evidence_ids)}
                      type="button"
                    >
                      查看证据
                    </button>
                  ) : null}
                </span>
                <p className="relationship-rationale">
                  {edge.rationale ?? (edge.source_tier ? `source tier ${edge.source_tier}` : "暂无说明")}
                </p>
              </li>
            ))}
          </ul>
          </>
        ) : (
          <p className="empty-note">
            展开一个节点后，这里会显示完整关系、basis、confidence 和证据数量。
          </p>
        )}
      </section>
      {isDetailOpen && runId ? (
        <div className="detail-drawer">
          <StockDetail
            entityId={seedEntity.id}
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

interface RelationRow {
  edge: Edge;
  source: EntityNode | undefined;
  target: EntityNode;
}

function entityLabel(entity: EntityNode | undefined): string {
  if (!entity) return "未知实体";
  return [entity.symbol, entity.name].filter(Boolean).join(" · ");
}
