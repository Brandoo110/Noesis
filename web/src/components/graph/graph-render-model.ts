import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import type { Basis, Edge, EntityNode, Relation } from "../../types/api";
import type { EdgeViewData } from "./EdgeView";
import type { EntityNodeViewData, ExpandVisualState } from "./EntityNodeView";

export interface GraphRenderNode {
  entity: EntityNode;
  expanded: boolean;
  expandState: ExpandVisualState;
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
  height: number;
  nodes: GraphRenderNode[];
  width: number;
}

export interface GraphRenderFilters {
  basisFilter: "all" | Basis;
  focusedEntityId?: string | null;
  relationFilter: "all" | Relation;
}

const BASE_STAGE_HEIGHT = 560;
const BASE_STAGE_WIDTH = 1240;
const COLUMN_GAP = 292;
const NODE_MARGIN = 64;
const ROW_GAP = 92;
const SEED_X = 170;
const RELATION_ORDER: Edge["relation"][] = [
  "competitor",
  "supplier",
  "customer",
  "belongs_to"
];

export function buildGraphRenderModel(
  seedEntity: EntityNode,
  nodes: FlowNode<EntityNodeViewData>[],
  edges: FlowEdge<EdgeViewData>[],
  filtersOrBasis: GraphRenderFilters | "all" | Basis
): GraphRenderModel {
  const filters = normalizeFilters(filtersOrBasis);
  const entityById = new Map(nodes.map((node) => [node.id, node.data.entity]));
  const expandedById = new Map(nodes.map((node) => [node.id, node.data.expanded]));
  const expandStateById = new Map(nodes.map((node) => [node.id, node.data.expandState]));
  const records = edges
    .map((flowEdge) => {
      const edge = flowEdge.data?.edge;
      if (!edge) return null;
      const source = entityById.get(flowEdge.source) ?? seedEntity;
      const target = entityById.get(flowEdge.target) ?? edge.neighbor;
      return { edge, source, sourceId: flowEdge.source, target };
    })
    .filter((record): record is EdgeRecord => record !== null);

  const positions = buildLayeredPositions(records, seedEntity.id);

  const visibleRecords = records.filter(
    (record) =>
      (filters.basisFilter === "all" || record.edge.basis === filters.basisFilter) &&
      (filters.relationFilter === "all" || record.edge.relation === filters.relationFilter) &&
      matchesFocus(record, filters.focusedEntityId)
  );
  const visibleIds = new Set<string>([seedEntity.id]);
  if (filters.focusedEntityId) {
    visibleIds.add(filters.focusedEntityId);
  }
  for (const record of visibleRecords) {
    visibleIds.add(record.source.id);
    visibleIds.add(record.target.id);
  }

  const renderNodes = Array.from(visibleIds).map((id) => {
    const entity = id === seedEntity.id ? seedEntity : entityById.get(id);
    if (!entity) return null;
    const point = positions.get(id) ?? fallbackPoint(id, visibleIds);
    const size = nodeSize(entity, id === seedEntity.id);
    return {
      entity,
      expanded: expandedById.get(id) ?? false,
      expandState: expandStateById.get(id) ?? { edgeCount: 0, status: "idle" },
      id,
      isSeed: id === seedEntity.id,
      left: point.x - size.w / 2,
      top: point.y - size.h / 2,
      x: point.x,
      y: point.y
    };
  }).filter((node): node is GraphRenderNode => node !== null);
  const renderNodeById = new Map(renderNodes.map((node) => [node.id, node]));
  const bounds = stageBounds(renderNodes);

  return {
    height: bounds.height,
    nodes: renderNodes,
    width: bounds.width,
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

function normalizeFilters(
  filtersOrBasis: GraphRenderFilters | "all" | Basis
): GraphRenderFilters {
  if (typeof filtersOrBasis === "string") {
    return {
      basisFilter: filtersOrBasis,
      focusedEntityId: null,
      relationFilter: "all"
    };
  }
  return filtersOrBasis;
}

function matchesFocus(record: EdgeRecord, focusedEntityId?: string | null): boolean {
  if (!focusedEntityId) return true;
  return record.sourceId === focusedEntityId || record.target.id === focusedEntityId;
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

function buildLayeredPositions(
  records: EdgeRecord[],
  seedEntityId: string
): Map<string, Point> {
  const outgoing = groupOutgoing(records);
  const depthById = graphDepths(outgoing, seedEntityId);
  const positions = new Map<string, Point>();
  const directRows = sortedChildren(outgoing.get(seedEntityId) ?? []);
  const directOffsets = rowOffsets(directRows);
  const directStartY = Math.max(
    NODE_MARGIN,
    (BASE_STAGE_HEIGHT - directOffsets.height) / 2
  );

  directRows.forEach((record, index) => {
    positions.set(record.target.id, {
      x: columnX(1),
      y: directStartY + directOffsets.offsets[index]
    });
  });

  positions.set(seedEntityId, {
    x: columnX(0),
    y: medianY(Array.from(positions.values()), BASE_STAGE_HEIGHT / 2)
  });

  const maxDepth = Math.max(1, ...Array.from(depthById.values()));
  for (let depth = 2; depth <= maxDepth; depth += 1) {
    placeDepthColumn(depth, outgoing, depthById, positions);
  }

  return positions;
}

function placeDepthColumn(
  depth: number,
  outgoing: Map<string, EdgeRecord[]>,
  depthById: Map<string, number>,
  positions: Map<string, Point>
): void {
  const rows: Array<{ id: string; order: number; y: number }> = [];
  const parentIds = Array.from(positions.keys())
    .filter((id) => depthById.get(id) === depth - 1)
    .sort((a, b) => (positions.get(a)?.y ?? 0) - (positions.get(b)?.y ?? 0));

  parentIds.forEach((parentId) => {
    const parent = positions.get(parentId);
    if (!parent) return;
    const children = sortedChildren(
      (outgoing.get(parentId) ?? []).filter(
        (record) => depthById.get(record.target.id) === depth
      )
    );
    children.forEach((record, index) => {
      if (positions.has(record.target.id)) return;
      rows.push({
        id: record.target.id,
        order: rows.length,
        y: parent.y + (index - (children.length - 1) / 2) * ROW_GAP
      });
    });
  });

  let nextY = NODE_MARGIN;
  for (const row of rows.sort((a, b) => a.y - b.y || a.order - b.order)) {
    const y = Math.max(row.y, nextY);
    positions.set(row.id, { x: columnX(depth), y });
    nextY = y + ROW_GAP;
  }
}

function groupOutgoing(records: EdgeRecord[]): Map<string, EdgeRecord[]> {
  const outgoing = new Map<string, EdgeRecord[]>();
  for (const record of records) {
    const group = outgoing.get(record.sourceId) ?? [];
    group.push(record);
    outgoing.set(record.sourceId, group);
  }
  return outgoing;
}

function graphDepths(
  outgoing: Map<string, EdgeRecord[]>,
  seedEntityId: string
): Map<string, number> {
  const depthById = new Map<string, number>([[seedEntityId, 0]]);
  const queue = [seedEntityId];
  while (queue.length > 0) {
    const sourceId = queue.shift();
    if (!sourceId) continue;
    const nextDepth = (depthById.get(sourceId) ?? 0) + 1;
    for (const record of outgoing.get(sourceId) ?? []) {
      if (depthById.has(record.target.id)) continue;
      depthById.set(record.target.id, nextDepth);
      queue.push(record.target.id);
    }
  }

  for (const records of outgoing.values()) {
    for (const record of records) {
      if (!depthById.has(record.sourceId)) {
        depthById.set(record.sourceId, 1);
      }
      if (!depthById.has(record.target.id)) {
        depthById.set(record.target.id, (depthById.get(record.sourceId) ?? 0) + 1);
      }
    }
  }

  return depthById;
}

function sortedChildren(records: EdgeRecord[]): EdgeRecord[] {
  return [...records].sort(compareRecords);
}

function compareRecords(a: EdgeRecord, b: EdgeRecord): number {
  const relationDelta =
    RELATION_ORDER.indexOf(a.edge.relation) - RELATION_ORDER.indexOf(b.edge.relation);
  if (relationDelta !== 0) return relationDelta;
  const typeDelta = nodeTypeWeight(a.target) - nodeTypeWeight(b.target);
  if (typeDelta !== 0) return typeDelta;
  return entityLabel(a.target).localeCompare(entityLabel(b.target));
}

function nodeTypeWeight(entity: EntityNode): number {
  return entity.node_type === "company" ? 0 : 1;
}

function rowOffsets(records: EdgeRecord[]): { height: number; offsets: number[] } {
  if (records.length === 0) return { height: 0, offsets: [] };
  let y = 0;
  let previousRelation: Edge["relation"] | null = null;
  const offsets: number[] = [];
  records.forEach((record, index) => {
    if (index > 0) {
      y += ROW_GAP;
      if (previousRelation !== record.edge.relation) {
        y += 24;
      }
    }
    offsets.push(y);
    previousRelation = record.edge.relation;
  });
  return { height: offsets[offsets.length - 1] ?? 0, offsets };
}

function medianY(points: Point[], fallback: number): number {
  if (points.length === 0) return fallback;
  const ys = points.map((point) => point.y).sort((a, b) => a - b);
  const middle = Math.floor(ys.length / 2);
  if (ys.length % 2 === 1) {
    return ys[middle];
  }
  return (ys[middle - 1] + ys[middle]) / 2;
}

function stageBounds(nodes: GraphRenderNode[]): { height: number; width: number } {
  const bottom = nodes.reduce(
    (max, node) => Math.max(max, node.top + nodeSize(node.entity, node.isSeed).h),
    0
  );
  const right = nodes.reduce(
    (max, node) => Math.max(max, node.left + nodeSize(node.entity, node.isSeed).w),
    0
  );
  return {
    height: Math.ceil(Math.max(BASE_STAGE_HEIGHT, bottom + NODE_MARGIN)),
    width: Math.ceil(Math.max(BASE_STAGE_WIDTH, right + NODE_MARGIN))
  };
}

function fallbackPoint(id: string, ids: Set<string>): Point {
  const index = Array.from(ids).indexOf(id);
  return {
    x: columnX(1 + Math.floor(index / 8)),
    y: NODE_MARGIN + (index % 8) * ROW_GAP
  };
}

function columnX(depth: number): number {
  return SEED_X + depth * COLUMN_GAP;
}

function entityLabel(entity: EntityNode): string {
  return entity.symbol ?? entity.name;
}
