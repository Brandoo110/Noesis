import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import { expandEntity } from "../api/client";
import type { Edge as ApiEdge, EntityNode } from "../types/api";
import type { EdgeViewData } from "../components/graph/EdgeView";
import type { EntityNodeViewData } from "../components/graph/EntityNodeView";

export interface UseExpandOptions {
  positionId: string;
  seedEntity: EntityNode;
  onViewDetail?: (entityId: string) => void;
}

export interface UseExpandResult {
  expand: (entityId: string) => Promise<void>;
  reset: () => void;
  nodes: FlowNode<EntityNodeViewData>[];
  edges: FlowEdge<EdgeViewData>[];
}

export function useExpand({
  onViewDetail,
  positionId,
  seedEntity
}: UseExpandOptions): UseExpandResult {
  const [entitiesById, setEntitiesById] = useState(() =>
    new Map([[seedEntity.id, seedEntity]])
  );
  const [edgesById, setEdgesById] = useState(
    () => new Map<string, FlowEdge<EdgeViewData>>()
  );
  const [expandedEntityIds, setExpandedEntityIds] = useState(
    () => new Set<string>()
  );
  const expandedRef = useRef(expandedEntityIds);

  useEffect(() => {
    setEntitiesById(new Map([[seedEntity.id, seedEntity]]));
    setEdgesById(new Map());
    setExpandedEntityIds(new Set());
  }, [positionId, seedEntity]);

  useEffect(() => {
    expandedRef.current = expandedEntityIds;
  }, [expandedEntityIds]);

  const expand = useCallback(
    async (entityId: string): Promise<void> => {
      if (expandedRef.current.has(entityId)) {
        return;
      }

      const result = await expandEntity(entityId, positionId);
      setEntitiesById((current) => {
        const next = new Map(current);
        for (const edge of result.edges) {
          next.set(edge.neighbor.id, edge.neighbor);
        }
        return next;
      });
      setEdgesById((current) => {
        const next = new Map(current);
        for (const edge of result.edges) {
          if (!next.has(edge.id)) {
            next.set(edge.id, toFlowEdge(entityId, edge));
          }
        }
        return next;
      });
      setExpandedEntityIds((current) => new Set(current).add(entityId));
    },
    [positionId]
  );

  const reset = useCallback((): void => {
    setEntitiesById(new Map([[seedEntity.id, seedEntity]]));
    setEdgesById(new Map());
    setExpandedEntityIds(new Set());
  }, [seedEntity]);

  const nodes = useMemo(
    () =>
      positionEntities(Array.from(entitiesById.values()), seedEntity.id).map(
        ({ entity, position }) =>
          toFlowNode(entity, position, {
            expanded: expandedEntityIds.has(entity.id),
            isSeed: entity.id === seedEntity.id,
            onExpand: expand,
            onViewDetail: entity.id === seedEntity.id ? onViewDetail : undefined
          })
      ),
    [entitiesById, expandedEntityIds, expand, onViewDetail, seedEntity.id]
  );

  return {
    expand,
    reset,
    nodes,
    edges: Array.from(edgesById.values())
  };
}

function toFlowNode(
  entity: EntityNode,
  position: { x: number; y: number },
  data: Omit<EntityNodeViewData, "entity">
): FlowNode<EntityNodeViewData> {
  return {
    id: entity.id,
    type: "entity",
    position,
    data: {
      ...data,
      entity
    }
  };
}

function positionEntities(
  entities: EntityNode[],
  seedEntityId: string
): Array<{ entity: EntityNode; position: { x: number; y: number } }> {
  const seed = entities.find((entity) => entity.id === seedEntityId);
  const companies = entities.filter(
    (entity) => entity.id !== seedEntityId && entity.node_type === "company"
  );
  const themes = entities.filter(
    (entity) => entity.id !== seedEntityId && entity.node_type !== "company"
  );

  return [
    ...(seed ? [{ entity: seed, position: { x: 0, y: 0 } }] : []),
    ...companies.map((entity, index) => ({
      entity,
      position: lanePosition("left", index, companies.length)
    })),
    ...themes.map((entity, index) => ({
      entity,
      position: lanePosition("right", index, themes.length)
    }))
  ];
}

function lanePosition(
  side: "left" | "right",
  index: number,
  total: number
): { x: number; y: number } {
  const sideSign = side === "left" ? -1 : 1;
  const rowsPerColumn = 4;
  const column = Math.floor(index / rowsPerColumn);
  const row = index % rowsPerColumn;
  const rowsInColumn = Math.min(rowsPerColumn, total - column * rowsPerColumn);
  const spacingY = 86;
  const x = sideSign * (190 + column * 180);
  const y = Math.round((row - (rowsInColumn - 1) / 2) * spacingY);

  return { x, y };
}

function toFlowEdge(fromEntityId: string, edge: ApiEdge): FlowEdge<EdgeViewData> {
  return {
    id: edge.id,
    source: fromEntityId,
    target: edge.neighbor.id,
    type: "edge",
    data: { edge }
  };
}
