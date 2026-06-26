import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import { expandEntity } from "../api/client";
import type { Edge as ApiEdge, EntityNode } from "../types/api";
import type { EdgeViewData } from "../components/graph/EdgeView";
import type { EntityNodeViewData } from "../components/graph/EntityNodeView";

export interface UseExpandOptions {
  positionId: string;
  seedEntity: EntityNode;
}

export interface UseExpandResult {
  expand: (entityId: string) => Promise<void>;
  nodes: FlowNode<EntityNodeViewData>[];
  edges: FlowEdge<EdgeViewData>[];
}

export function useExpand({
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

  const nodes = useMemo(
    () =>
      Array.from(entitiesById.values()).map((entity, index) =>
        toFlowNode(entity, index, {
          expanded: expandedEntityIds.has(entity.id),
          isSeed: entity.id === seedEntity.id,
          onExpand: expand
        })
      ),
    [entitiesById, expandedEntityIds, expand, seedEntity.id]
  );

  return {
    expand,
    nodes,
    edges: Array.from(edgesById.values())
  };
}

function toFlowNode(
  entity: EntityNode,
  index: number,
  data: Omit<EntityNodeViewData, "entity">
): FlowNode<EntityNodeViewData> {
  return {
    id: entity.id,
    type: "entity",
    position: {
      x: index === 0 ? 0 : 240 * index,
      y: index === 0 ? 0 : 80 * (index % 2)
    },
    data: {
      ...data,
      entity
    }
  };
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
