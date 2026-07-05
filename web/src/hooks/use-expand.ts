import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import { expandEntity } from "../api/client";
import type { Edge as ApiEdge, EntityNode } from "../types/api";
import type { EdgeViewData } from "../components/graph/EdgeView";
import type {
  EntityNodeViewData,
  ExpandVisualState,
  ExpandVisualStatus
} from "../components/graph/EntityNodeView";

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
  notice: ExpandNotice | null;
}

export interface ExpandNotice {
  entityId: string;
  message: string;
  tone: "error" | "info" | "success" | "warning";
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
  const [expandStateById, setExpandStateById] = useState(
    () => new Map<string, ExpandVisualState>()
  );
  const [notice, setNotice] = useState<ExpandNotice | null>(null);
  const entitiesRef = useRef(entitiesById);
  const expandedRef = useRef(expandedEntityIds);
  const expandStateRef = useRef(expandStateById);

  useEffect(() => {
    setEntitiesById(new Map([[seedEntity.id, seedEntity]]));
    setEdgesById(new Map());
    setExpandedEntityIds(new Set());
    setExpandStateById(new Map());
    setNotice(null);
  }, [positionId, seedEntity]);

  useEffect(() => {
    expandedRef.current = expandedEntityIds;
  }, [expandedEntityIds]);

  useEffect(() => {
    entitiesRef.current = entitiesById;
  }, [entitiesById]);

  useEffect(() => {
    expandStateRef.current = expandStateById;
  }, [expandStateById]);

  const expand = useCallback(
    async (entityId: string): Promise<void> => {
      const currentState = expandStateRef.current.get(entityId);
      if (
        expandedRef.current.has(entityId) ||
        currentState?.status === "loading"
      ) {
        return;
      }

      setExpandStateById((current) =>
        withExpandState(current, entityId, { edgeCount: 0, status: "loading" })
      );
      setNotice(null);

      try {
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
        const edgeCount = result.edges.length;
        const status = expandStatusFromResult(result.status, edgeCount);
        setExpandStateById((current) =>
          withExpandState(current, entityId, {
            edgeCount,
            runId: result.run_id,
            status
          })
        );
        setExpandedEntityIds((current) => new Set(current).add(entityId));
        setNotice({
          entityId,
          message: noticeMessage(
            entityLabel(entitiesRef.current.get(entityId), entityId),
            status,
            edgeCount
          ),
          tone: noticeTone(status)
        });
      } catch (error) {
        const message = toErrorMessage(error);
        setExpandStateById((current) =>
          withExpandState(current, entityId, {
            edgeCount: 0,
            message,
            status: "failed"
          })
        );
        setNotice({
          entityId,
          message: `${entityLabel(entitiesRef.current.get(entityId), entityId)} 展开失败：${message}`,
          tone: "error"
        });
      }
    },
    [positionId]
  );

  const reset = useCallback((): void => {
    setEntitiesById(new Map([[seedEntity.id, seedEntity]]));
    setEdgesById(new Map());
    setExpandedEntityIds(new Set());
    setExpandStateById(new Map());
    setNotice(null);
  }, [seedEntity]);

  const nodes = useMemo(
    () =>
      positionEntities(Array.from(entitiesById.values()), seedEntity.id).map(
        ({ entity, position }) =>
          toFlowNode(entity, position, {
            expanded: expandedEntityIds.has(entity.id),
            expandState: expandStateById.get(entity.id) ?? idleExpandState(),
            isSeed: entity.id === seedEntity.id,
            onExpand: expand,
            onViewDetail: entity.id === seedEntity.id ? onViewDetail : undefined
          })
      ),
    [entitiesById, expand, expandStateById, expandedEntityIds, onViewDetail, seedEntity.id]
  );

  return {
    expand,
    reset,
    nodes,
    edges: Array.from(edgesById.values()),
    notice
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

function withExpandState(
  current: Map<string, ExpandVisualState>,
  entityId: string,
  state: ExpandVisualState
): Map<string, ExpandVisualState> {
  const next = new Map(current);
  next.set(entityId, state);
  return next;
}

function idleExpandState(): ExpandVisualState {
  return { edgeCount: 0, status: "idle" };
}

function expandStatusFromResult(
  resultStatus: "cached" | "completed",
  edgeCount: number
): ExpandVisualStatus {
  if (edgeCount === 0) return "empty";
  return resultStatus === "cached" ? "cached" : "expanded";
}

function noticeMessage(label: string, status: ExpandVisualStatus, edgeCount: number): string {
  if (status === "cached") {
    return `${label} 使用缓存结果，显示 ${edgeCount} 条关系。`;
  }
  if (status === "empty") {
    return `${label} 未发现新增一跳关系。`;
  }
  return `${label} 已展开 ${edgeCount} 条关系。`;
}

function noticeTone(status: ExpandVisualStatus): ExpandNotice["tone"] {
  if (status === "empty") return "warning";
  return "success";
}

function entityLabel(entity: EntityNode | undefined, fallback: string): string {
  return entity?.name || entity?.symbol || fallback;
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "unknown error";
}
