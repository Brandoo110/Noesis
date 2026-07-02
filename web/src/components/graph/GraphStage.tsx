import type { CSSProperties } from "react";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import type { Basis, Edge, EntityNode } from "../../types/api";
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
  nodes: FlowNode<EntityNodeViewData>[];
  onExpandNode: (entityId: string) => void;
  onOpenEvidence: (evidenceIds: string[]) => void;
  onSeedDetail?: () => void;
  seedEntity: EntityNode;
}

const RELATION_LABELS: Record<Edge["relation"], string> = {
  belongs_to: "归属",
  competitor: "竞争",
  customer: "客户",
  supplier: "供应商"
};

export function GraphStage({
  basisFilter,
  edges,
  nodes,
  onExpandNode,
  onOpenEvidence,
  onSeedDetail,
  seedEntity
}: GraphStageProps): JSX.Element {
  const model = buildGraphRenderModel(seedEntity, nodes, edges, basisFilter);
  return (
    <>
      <div className="graph-canvas">
        <div className="graph-stage" data-testid="graph-stage">
          <svg aria-label="图谱边" height="560" viewBox="0 0 1240 560" width="1240">
            {model.edges.map((edge) => (
              <g key={edge.edge.id}>
                <line
                  className={edge.edge.basis === "source_backed" ? "edge-source-backed" : "edge-inferred"}
                  data-testid={`edge-path-${edge.edge.id}`}
                  strokeDasharray={edge.edge.basis === "inferred" ? "6 5" : undefined}
                  x1={edge.from.x}
                  x2={edge.to.x}
                  y1={edge.from.y}
                  y2={edge.to.y}
                />
                <text
                  className="edge-label"
                  x={(edge.from.x + edge.to.x) / 2}
                  y={(edge.from.y + edge.to.y) / 2 - 6}
                >
                  {RELATION_LABELS[edge.edge.relation]}
                </text>
              </g>
            ))}
          </svg>
          {model.nodes.map((node) => (
            <GraphNodeButton
              key={node.id}
              node={node}
              onExpandNode={onExpandNode}
              onSeedDetail={onSeedDetail}
            />
          ))}
        </div>
      </div>
      <RelationshipList
        edges={model.edges}
        onOpenEvidence={onOpenEvidence}
      />
    </>
  );
}

function GraphNodeButton({
  node,
  onExpandNode,
  onSeedDetail
}: {
  node: GraphRenderNode;
  onExpandNode: (entityId: string) => void;
  onSeedDetail?: () => void;
}): JSX.Element {
  const size = nodeSize(node.entity, node.isSeed);
  const canExpand = !node.expanded;
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
        className={graphNodeClass(node)}
        data-testid={`graph-node-${node.id}`}
        onClick={() => {
          if (node.isSeed && onSeedDetail) {
            onSeedDetail();
            return;
          }
          if (!node.expanded) {
            onExpandNode(node.id);
          }
        }}
        title={node.isSeed ? "持仓种子 · 点击查看个股详情" : node.entity.name}
        type="button"
      >
        {node.entity.symbol ? <strong>{node.entity.symbol}</strong> : null}
        <span>{node.entity.name}</span>
      </button>
      {canExpand ? (
        <button
          aria-label={`展开 ${label}`}
          className="graph-expand-badge"
          onClick={() => onExpandNode(node.id)}
          title="点击展开产业链（懒加载）"
          type="button"
        >
          +
        </button>
      ) : null}
    </div>
  );
}

function RelationshipList({
  edges,
  onOpenEvidence
}: {
  edges: GraphRenderEdge[];
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
        <p className="empty-note">当前 basis 筛选下暂无匹配关系。</p>
      )}
    </section>
  );
}

function graphNodeClass(node: GraphRenderNode): string {
  if (node.isSeed) return "graph-node seed-node";
  const typeClass = node.entity.node_type === "company" ? "company-node" : "segment-node";
  return `graph-node ${typeClass}`;
}

function entityLabel(entity: EntityNode): string {
  return entity.symbol ?? entity.name;
}
