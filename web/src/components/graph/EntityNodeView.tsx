import type { NodeProps } from "reactflow";

import { nodeClassName, nodeStyle } from "../../lib/visual";
import type { EntityNode } from "../../types/api";

export interface EntityNodeViewData {
  entity: EntityNode;
  expanded: boolean;
  isSeed: boolean;
  onExpand?: (entityId: string) => void;
  onViewDetail?: (entityId: string) => void;
}

export function EntityNodeView({
  data
}: NodeProps<EntityNodeViewData>): JSX.Element {
  const { entity } = data;
  return (
    <article
      className={nodeClassName(entity.node_type, data.isSeed)}
      data-testid={`entity-node-${entity.id}`}
      style={nodeStyle(entity.node_type, data.isSeed)}
    >
      <strong>{entity.symbol ?? entity.name}</strong>
      <span>{entity.name}</span>
      <small>{entity.node_type}</small>
      {data.onExpand ? (
        <button
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
          onClick={() => data.onViewDetail?.(entity.id)}
          type="button"
        >
          详情
        </button>
      ) : null}
    </article>
  );
}
