import { useEffect, useRef, useState, type CSSProperties, type MouseEvent } from "react";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import type { Basis, Edge, EntityNode, Relation } from "../../types/api";
import type { EdgeViewData } from "./EdgeView";
import type { EntityNodeViewData } from "./EntityNodeView";
import {
  buildGraphRenderModel,
  nodeSize,
  type GraphRenderEdge,
  type GraphRenderNode
} from "./graph-render-model";

interface GraphStageProps {
  basisFilter: "all" | Basis;
  edges: FlowEdge<EdgeViewData>[];
  focusedEntityId: string | null;
  nodes: FlowNode<EntityNodeViewData>[];
  onClearFocus: () => void;
  onExpandNode: (entityId: string) => void;
  onFocusNode: (entityId: string) => void;
  onOpenEvidence: (evidenceIds: string[]) => void;
  onRelationFilterChange: (relation: "all" | Relation) => void;
  onSeedDetail?: () => void;
  relationFilter: "all" | Relation;
  seedEntity: EntityNode;
}

const RELATION_LABELS: Record<Edge["relation"], string> = {
  belongs_to: "归属",
  competitor: "竞争",
  customer: "客户",
  supplier: "供应商"
};
const RELATION_LEGEND_ORDER: Edge["relation"][] = [
  "competitor",
  "supplier",
  "customer",
  "belongs_to"
];
const RELATION_CLASS_NAMES: Record<Edge["relation"], string> = {
  belongs_to: "edge-relation-belongs_to",
  competitor: "edge-relation-competitor",
  customer: "edge-relation-customer",
  supplier: "edge-relation-supplier"
};
const MIN_ZOOM = 0.7;
const MAX_ZOOM = 1.6;
const ZOOM_STEP = 0.15;

export function GraphStage({
  basisFilter,
  edges,
  focusedEntityId,
  nodes,
  onClearFocus,
  onExpandNode,
  onFocusNode,
  onOpenEvidence,
  onRelationFilterChange,
  onSeedDetail,
  relationFilter,
  seedEntity
}: GraphStageProps): JSX.Element {
  const model = buildGraphRenderModel(seedEntity, nodes, edges, {
    basisFilter,
    focusedEntityId,
    relationFilter
  });
  const [zoom, setZoom] = useState(1);
  const scrollPlaneRef = useRef<HTMLDivElement | null>(null);
  const canvasStyle = {
    "--graph-canvas-h": `${model.height}px`
  } as CSSProperties;
  const stageStyle = {
    "--graph-stage-h": `${model.height}px`,
    "--graph-stage-scale": formatZoomNumber(zoom),
    "--graph-stage-w": `${model.width}px`
  } as CSSProperties;
  const stageShellStyle = {
    "--graph-stage-scale": formatZoomNumber(zoom),
    "--graph-stage-scaled-h": `${Math.round(model.height * zoom)}px`,
    "--graph-stage-scaled-w": `${Math.round(model.width * zoom)}px`
  } as CSSProperties;
  const focusedNode = focusedEntityId
    ? model.nodes.find((node) => node.id === focusedEntityId)
    : null;

  useEffect(() => {
    const plane = scrollPlaneRef.current;
    if (!plane) {
      return;
    }
    const stablePlane: HTMLDivElement = plane;

    function handlePinchWheel(event: WheelEvent): void {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();

      const rect = stablePlane.getBoundingClientRect();
      const viewportX = clampNumber(
        event.clientX - rect.left,
        0,
        stablePlane.clientWidth || rect.width || 0
      );
      const viewportY = clampNumber(
        event.clientY - rect.top,
        0,
        stablePlane.clientHeight || rect.height || 0
      );

      setZoom((current) => {
        const next = clampZoom(current * Math.exp(-event.deltaY * 0.0015));
        if (next === current) {
          return current;
        }

        const contentX = (stablePlane.scrollLeft + viewportX) / current;
        const contentY = (stablePlane.scrollTop + viewportY) / current;
        window.requestAnimationFrame(() => {
          stablePlane.scrollLeft = Math.max(0, contentX * next - viewportX);
          stablePlane.scrollTop = Math.max(0, contentY * next - viewportY);
        });

        return next;
      });
    }

    stablePlane.addEventListener("wheel", handlePinchWheel, { passive: false });
    return () => {
      stablePlane.removeEventListener("wheel", handlePinchWheel);
    };
  }, []);

  function handleZoomIn(): void {
    setZoom((current) => clampZoom(current + ZOOM_STEP));
  }
  function handleZoomOut(): void {
    setZoom((current) => clampZoom(current - ZOOM_STEP));
  }
  function handleResetZoom(): void {
    setZoom(1);
  }
  function handleStageBackgroundClick(event: MouseEvent<HTMLDivElement | SVGSVGElement>): void {
    if (!focusedEntityId) {
      return;
    }
    const target = event.target;
    if (target === event.currentTarget || target instanceof SVGSVGElement) {
      onClearFocus();
    }
  }
  return (
    <>
      <div className="graph-canvas" data-testid="graph-canvas" style={canvasStyle}>
        <div className="graph-scroll-plane" data-testid="graph-scroll-plane" ref={scrollPlaneRef}>
          <div
            className="graph-stage-shell"
            data-testid="graph-stage-shell"
            onClick={handleStageBackgroundClick}
            style={stageShellStyle}
          >
            <div
              className="graph-stage"
              data-testid="graph-stage"
              onClick={handleStageBackgroundClick}
              style={stageStyle}
            >
              <svg
                aria-label="图谱边"
                height={model.height}
                onClick={handleStageBackgroundClick}
                viewBox={`0 0 ${model.width} ${model.height}`}
                width={model.width}
              >
                {model.edges.map((edge) => {
                  const from = edgeAnchor(edge.from, edge.to);
                  const to = edgeAnchor(edge.to, edge.from);
                  return (
                    <g key={edge.edge.id}>
                      <line
                        className={
                          edge.edge.basis === "source_backed"
                            ? `edge-source-backed ${RELATION_CLASS_NAMES[edge.edge.relation]}`
                            : `edge-inferred ${RELATION_CLASS_NAMES[edge.edge.relation]}`
                        }
                        data-testid={`edge-path-${edge.edge.id}`}
                        x1={from.x}
                        x2={to.x}
                        y1={from.y}
                        y2={to.y}
                      />
                      <title>
                        {`${entityLabel(edge.source)} → ${entityLabel(edge.target)} · ${RELATION_LABELS[edge.edge.relation]} · ${Math.round(edge.edge.confidence * 100)}%`}
                      </title>
                    </g>
                  );
                })}
              </svg>
              {model.nodes.map((node) => (
                <GraphNodeButton
                  key={node.id}
                  node={node}
                  isFocused={focusedEntityId === node.id}
                  onExpandNode={onExpandNode}
                  onFocusNode={onFocusNode}
                  onSeedDetail={onSeedDetail}
                />
              ))}
            </div>
          </div>
        </div>
        <RelationLegend
          onRelationFilterChange={onRelationFilterChange}
          relationFilter={relationFilter}
        />
        <GraphZoomControls
          onResetZoom={handleResetZoom}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          zoom={zoom}
        />
        {focusedNode ? (
          <div className="graph-focus-banner">
            <span>{`聚焦：${entityLabel(focusedNode.entity)}`}</span>
            <button onClick={onClearFocus} type="button">清除聚焦</button>
          </div>
        ) : null}
      </div>
      <RelationshipList
        edges={model.edges}
        focused={focusedNode !== null}
        onOpenEvidence={onOpenEvidence}
      />
    </>
  );
}

function clampZoom(value: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100));
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function formatZoomNumber(value: number): string {
  return Number(value.toFixed(2)).toString();
}

function formatZoomLabel(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function edgeAnchor(from: GraphRenderNode, to: GraphRenderNode): { x: number; y: number } {
  const size = nodeSize(from.entity, from.isSeed);
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    return {
      x: from.x + Math.sign(dx || 1) * (size.w / 2),
      y: from.y
    };
  }
  return {
    x: from.x,
    y: from.y + Math.sign(dy || 1) * (size.h / 2)
  };
}

function RelationLegend({
  onRelationFilterChange,
  relationFilter
}: {
  onRelationFilterChange: (relation: "all" | Relation) => void;
  relationFilter: "all" | Relation;
}): JSX.Element {
  return (
    <aside aria-label="关系类型图例" className="relation-legend">
      <strong>关系类型</strong>
      <button
        aria-label="显示全部关系类型"
        aria-pressed={relationFilter === "all"}
        className="relation-legend-button relation-legend-all"
        onClick={() => onRelationFilterChange("all")}
        type="button"
      >
        全部
      </button>
      {RELATION_LEGEND_ORDER.map((relation) => (
        <button
          aria-label={`只看${RELATION_LABELS[relation]}关系`}
          aria-pressed={relationFilter === relation}
          className="relation-legend-button"
          key={relation}
          onClick={() => onRelationFilterChange(relation)}
          type="button"
        >
          <i className={`relation-swatch ${RELATION_CLASS_NAMES[relation]}`} />
          {RELATION_LABELS[relation]}
        </button>
      ))}
    </aside>
  );
}

function GraphZoomControls({
  onResetZoom,
  onZoomIn,
  onZoomOut,
  zoom
}: {
  onResetZoom: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  zoom: number;
}): JSX.Element {
  return (
    <div aria-label="图谱缩放" className="graph-zoom-controls" role="group">
      <button
        aria-label="缩小图谱"
        disabled={zoom <= MIN_ZOOM}
        onClick={onZoomOut}
        type="button"
      >
        -
      </button>
      <span aria-label="当前缩放比例">{formatZoomLabel(zoom)}</span>
      <button
        aria-label="放大图谱"
        disabled={zoom >= MAX_ZOOM}
        onClick={onZoomIn}
        type="button"
      >
        +
      </button>
      <button aria-label="重置缩放" onClick={onResetZoom} type="button">
        100%
      </button>
    </div>
  );
}

function GraphNodeButton({
  isFocused,
  node,
  onExpandNode,
  onFocusNode,
  onSeedDetail
}: {
  isFocused: boolean;
  node: GraphRenderNode;
  onExpandNode: (entityId: string) => void;
  onFocusNode: (entityId: string) => void;
  onSeedDetail?: () => void;
}): JSX.Element {
  const size = nodeSize(node.entity, node.isSeed);
  const label = node.entity.name || node.entity.symbol || node.id;
  return (
    <div
      className="graph-node-shell"
      style={{
        "--h": `${size.h}px`,
        "--w": `${size.w}px`,
        "--x": `${node.left}px`,
        "--y": `${node.top}px`
      } as CSSProperties}
    >
      <button
        className={graphNodeClass(node, isFocused)}
        data-testid={`graph-node-${node.id}`}
        onClick={() => {
          if (node.isSeed && onSeedDetail) {
            onSeedDetail();
            return;
          }
          if (!node.isSeed) {
            onFocusNode(node.id);
          }
        }}
        title={node.isSeed ? "持仓种子 · 点击查看个股详情" : "点击聚焦这个节点的关系邻域"}
        type="button"
      >
        {node.entity.symbol ? <strong>{node.entity.symbol}</strong> : null}
        <span>{node.entity.name}</span>
      </button>
      <ExpandStateBadge label={label} node={node} onExpandNode={onExpandNode} />
    </div>
  );
}

function ExpandStateBadge({
  label,
  node,
  onExpandNode
}: {
  label: string;
  node: GraphRenderNode;
  onExpandNode: (entityId: string) => void;
}): JSX.Element {
  const state = node.expandState;
  if (state.status === "loading") {
    return (
      <button
        aria-label={`调研中 ${label}`}
        className="graph-expand-badge is-loading"
        disabled
        title="调研中"
        type="button"
      >
        调研中
      </button>
    );
  }
  if (state.status === "failed") {
    return (
      <button
        aria-label={`重试调研 ${label}`}
        className="graph-expand-badge is-failed"
        onClick={() => onExpandNode(node.id)}
        title={state.message ? `上次失败：${state.message}` : "上次调研失败，点击重试"}
        type="button"
      >
        !
      </button>
    );
  }
  if (state.status === "empty") {
    return (
      <span
        aria-label={`${label} 无新增关系`}
        className="graph-expand-badge is-empty"
        title="已研究，未发现新增一跳关系"
      >
        0
      </span>
    );
  }
  if (state.status === "expanded" || state.status === "cached") {
    return (
      <span
        aria-label={`${label} 已展开 ${state.edgeCount} 条关系`}
        className={expandedBadgeClass(state.status)}
        title={state.status === "cached" ? "缓存命中" : "已展开"}
      >
        {state.edgeCount}
      </span>
    );
  }
  return (
    <button
      aria-label={`调研 ${label}`}
      className="graph-expand-badge is-research"
      onClick={() => onExpandNode(node.id)}
      title="调研该节点的一跳关键关系"
      type="button"
    >
      调研
    </button>
  );
}

function RelationshipList({
  edges,
  focused,
  onOpenEvidence
}: {
  edges: GraphRenderEdge[];
  focused: boolean;
  onOpenEvidence: (evidenceIds: string[]) => void;
}): JSX.Element {
  return (
    <section aria-label="关系清单" className="card relationships-card">
      <header className="relationship-head">
        <div>
          <p className="eyebrow">RELATIONSHIP EVIDENCE</p>
          <h2>当前关系</h2>
        </div>
        <span className="count-pill">{edges.length}</span>
      </header>
      {edges.length > 0 ? (
        <>
          <div className="relationship-table-head" aria-hidden="true">
            <span>FROM → TO</span>
            <span>关系</span>
            <span>BASIS</span>
            <span>置信</span>
            <span>证据</span>
            <span>说明</span>
          </div>
          {edges.map((edge) => (
            <div className="relationship-row" key={edge.edge.id}>
              <strong>{`${entityLabel(edge.source)} → ${entityLabel(edge.target)}`}</strong>
              <span>{RELATION_LABELS[edge.edge.relation]}</span>
              <span className={`basis-badge ${edge.edge.basis}`}>
                {edge.edge.basis === "source_backed" ? "source" : "inferred"}
              </span>
              <span className="mono">{`${Math.round(edge.edge.confidence * 100)}%`}</span>
              <span className="evidence-cell">
                <b>{edge.edge.evidence_ids.length}</b>
                {edge.edge.evidence_ids.length > 0 ? (
                  <button onClick={() => onOpenEvidence(edge.edge.evidence_ids)} type="button">
                    查看证据
                  </button>
                ) : null}
              </span>
              <span>{edge.edge.rationale ?? "暂无说明"}</span>
            </div>
          ))}
        </>
      ) : (
        <p className="empty-note">
          {focused ? "当前聚焦节点和筛选条件下暂无匹配关系。" : "当前筛选条件下暂无匹配关系。"}
        </p>
      )}
    </section>
  );
}

function expandedBadgeClass(status: "cached" | "expanded"): string {
  return status === "cached"
    ? "graph-expand-badge is-cached"
    : "graph-expand-badge is-expanded";
}

function graphNodeClass(node: GraphRenderNode, isFocused: boolean): string {
  const focusedClass = isFocused ? " is-focused" : "";
  if (node.isSeed) return `graph-node seed-node${focusedClass}`;
  const typeClass = node.entity.node_type === "company" ? "company-node" : "segment-node";
  return `graph-node ${typeClass}${focusedClass}`;
}

function entityLabel(entity: EntityNode): string {
  return entity.symbol ?? entity.name;
}
