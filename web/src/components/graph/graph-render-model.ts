import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import type { Basis, Edge, EntityNode } from "../../types/api";
import type { EdgeViewData } from "./EdgeView";
import type { EntityNodeViewData } from "./EntityNodeView";

export interface GraphRenderNode {
  entity: EntityNode;
  expanded: boolean;
  id: string;
  isSeed: boolean;
  left: number;
  top: number;
  x: number;
  y: number;
}

export interface GraphRenderEdge {
  edge: Edge;
  from: GraphRenderNode;
  source: EntityNode;
  target: EntityNode;
  to: GraphRenderNode;
}

export interface GraphRenderModel {
  edges: GraphRenderEdge[];
  nodes: GraphRenderNode[];
}

const SEED_POINT = { x: 620, y: 280 };
const RELATION_ORDER: Edge["relation"][] = [
  "supplier",
  "customer",
  "competitor",
  "belongs_to"
];

export function buildGraphRenderModel(
  seedEntity: EntityNode,
  nodes: FlowNode<EntityNodeViewData>[],
  edges: FlowEdge<EdgeViewData>[],
  basisFilter: "all" | Basis
): GraphRenderModel {
  const entityById = new Map(nodes.map((node) => [node.id, node.data.entity]));
  const expandedById = new Map(nodes.map((node) => [node.id, node.data.expanded]));
  const records = edges
    .map((flowEdge) => {
      const edge = flowEdge.data?.edge;
      if (!edge) return null;
      const source = entityById.get(flowEdge.source) ?? seedEntity;
      const target = entityById.get(flowEdge.target) ?? edge.neighbor;
      return { edge, source, sourceId: flowEdge.source, target };
    })
    .filter((record): record is EdgeRecord => record !== null);

  const positions = new Map<string, Point>([[seedEntity.id, SEED_POINT]]);
  placeDirectEdges(records, positions, seedEntity.id);
  placeChildEdges(records, positions, seedEntity.id);

  const visibleRecords = records.filter(
    (record) => basisFilter === "all" || record.edge.basis === basisFilter
  );
  const visibleIds = new Set<string>([seedEntity.id]);
  for (const record of visibleRecords) {
    visibleIds.add(record.source.id);
    visibleIds.add(record.target.id);
  }

  const renderNodes = Array.from(visibleIds).map((id) => {
    const entity = id === seedEntity.id ? seedEntity : entityById.get(id);
    if (!entity) return null;
    const point = positions.get(id) ?? SEED_POINT;
    const size = nodeSize(entity, id === seedEntity.id);
    return {
      entity,
      expanded: expandedById.get(id) ?? false,
      id,
      isSeed: id === seedEntity.id,
      left: point.x - size.w / 2,
      top: point.y - size.h / 2,
      x: point.x,
      y: point.y
    };
  }).filter((node): node is GraphRenderNode => node !== null);
  const renderNodeById = new Map(renderNodes.map((node) => [node.id, node]));

  return {
    nodes: renderNodes,
    edges: visibleRecords
      .map((record) => {
        const from = renderNodeById.get(record.source.id);
        const to = renderNodeById.get(record.target.id);
        if (!from || !to) return null;
        return {
          edge: record.edge,
          from,
          source: record.source,
          target: record.target,
          to
        };
      })
      .filter((edge): edge is GraphRenderEdge => edge !== null)
  };
}

export function nodeSize(
  entity: EntityNode,
  isSeed: boolean
): { h: number; w: number } {
  if (isSeed) return { h: 62, w: 172 };
  if (entity.node_type === "company") return { h: 54, w: 150 };
  return { h: 42, w: 190 };
}

interface EdgeRecord {
  edge: Edge;
  source: EntityNode;
  sourceId: string;
  target: EntityNode;
}

interface Point {
  x: number;
  y: number;
}

function placeDirectEdges(
  records: EdgeRecord[],
  positions: Map<string, Point>,
  seedEntityId: string
): void {
  for (const relation of RELATION_ORDER) {
    const group = records.filter(
      (record) => record.sourceId === seedEntityId && record.edge.relation === relation
    );
    group.forEach((record, index) => {
      positions.set(record.target.id, directPosition(relation, index, group.length));
    });
  }
}

function placeChildEdges(
  records: EdgeRecord[],
  positions: Map<string, Point>,
  seedEntityId: string
): void {
  const sourceIds = Array.from(new Set(records.map((record) => record.sourceId)))
    .filter((sourceId) => sourceId !== seedEntityId);
  for (const sourceId of sourceIds) {
    const parent = positions.get(sourceId);
    if (!parent) continue;
    const children = records.filter((record) => record.sourceId === sourceId);
    children.forEach((record, index) => {
      positions.set(record.target.id, {
        x: clampX(parent.x - 236),
        y: parent.y + (index - (children.length - 1) / 2) * 118
      });
    });
  }
}

function directPosition(
  relation: Edge["relation"],
  index: number,
  count: number
): Point {
  if (relation === "supplier") {
    return { x: 300, y: 280 + (index - (count - 1) / 2) * 140 };
  }
  if (relation === "customer") {
    return { x: 940, y: 280 + (index - (count - 1) / 2) * 140 };
  }
  if (relation === "competitor") {
    return { x: 620 + (index - (count - 1) / 2) * 240, y: 88 };
  }
  return { x: 620 + (index - (count - 1) / 2) * 300, y: 488 };
}

function clampX(x: number): number {
  return Math.max(90, Math.min(1150, x));
}
