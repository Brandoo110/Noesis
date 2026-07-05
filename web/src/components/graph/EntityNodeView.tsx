import { Handle, Position as FlowPosition, type NodeProps } from "reactflow";

import { nodeClassName, nodeStyle } from "../../lib/visual";
import type { EntityNode } from "../../types/api";

export type ExpandVisualStatus = "cached" | "empty" | "expanded" | "failed" | "idle" | "loading";

export interface ExpandVisualState {
  edgeCount: number;
  message?: string;
  runId?: string;
  status: ExpandVisualStatus;
}

export interface EntityNodeViewData {
  entity: EntityNode;
  expanded: boolean;
  expandState?: ExpandVisualState;
  isSeed: boolean;
  onExpand?: (entityId: string) => void;
  onViewDetail?: (entityId: string) => void;
}

export function EntityNodeView({
  data,
  isConnectable
}: NodeProps<EntityNodeViewData>): JSX.Element {
  const { entity } = data;
  return (
    <article
      className={nodeClassName(entity.node_type, data.isSeed)}
      data-testid={`entity-node-${entity.id}`}
      style={nodeStyle(entity.node_type, data.isSeed)}
      title={[entity.symbol, entity.name].filter(Boolean).join(" · ")}
    >
      <Handle
        data-testid={`target-handle-${entity.id}`}
        isConnectable={isConnectable}
        position={FlowPosition.Left}
        type="target"
      />
      <div className="node-heading">
        <span className="node-glyph" aria-hidden="true">{nodeGlyph(entity.node_type)}</span>
        <span>
          <strong>{entity.symbol ?? entity.name}</strong>
          <span>{entity.name}</span>
        </span>
      </div>
      <small>{data.isSeed ? "持仓种子" : nodeTypeLabel(entity.node_type)}</small>
      <div className="node-actions">
      {data.onExpand ? (
        <button
          className="nodrag nopan"
          disabled={data.expanded}
          onClick={() => data.onExpand?.(entity.id)}
          type="button"
        >
          {data.expanded ? "已展开" : "展开"}
        </button>
      ) : null}
      {data.isSeed && data.onViewDetail ? (
        <button
          aria-label={`详情 ${entity.symbol ?? entity.name}`}
          className="nodrag nopan"
          onClick={() => data.onViewDetail?.(entity.id)}
          type="button"
        >
          详情
        </button>
      ) : null}
      </div>
      <Handle
        data-testid={`source-handle-${entity.id}`}
        isConnectable={isConnectable}
        position={FlowPosition.Right}
        type="source"
      />
    </article>
  );
}

function nodeTypeLabel(nodeType: EntityNode["node_type"]): string {
  if (nodeType === "company") {
    return "公司";
  }
  if (nodeType === "segment") {
    return "产业段";
  }
  return "主题";
}

function nodeGlyph(nodeType: EntityNode["node_type"]): string {
  if (nodeType === "company") {
    return "C";
  }
  if (nodeType === "segment") {
    return "S";
  }
  return "T";
}
