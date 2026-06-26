import type { EdgeProps } from "reactflow";

import { edgeClassName, edgeStyle } from "../../lib/visual";
import type { Edge } from "../../types/api";

export interface EdgeViewData {
  edge: Edge;
}

export function EdgeView({
  data,
  id,
  sourceX,
  sourceY,
  targetX,
  targetY
}: EdgeProps<EdgeViewData>): JSX.Element {
  const edge = data?.edge;
  const basis = edge?.basis ?? "inferred";
  const style = edgeStyle(basis);
  const labelX = (sourceX + targetX) / 2;
  const labelY = (sourceY + targetY) / 2;

  return (
    <g data-testid={`edge-${id}`}>
      <path
        className={edgeClassName(basis)}
        d={`M ${sourceX} ${sourceY} L ${targetX} ${targetY}`}
        data-testid={`edge-path-${id}`}
        fill="none"
        style={style}
      />
      {edge ? (
        <text x={labelX} y={labelY}>
          {edge.rationale ? <title>{edge.rationale}</title> : null}
          {edge.relation} {Math.round(edge.confidence * 100)}%
        </text>
      ) : null}
    </g>
  );
}
