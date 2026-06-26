import type { EdgeProps } from "reactflow";

import { useEvidenceDrawer } from "../../context/evidence-drawer";
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
  const evidenceDrawer = useEvidenceDrawer();
  const edge = data?.edge;
  const basis = edge?.basis ?? "inferred";
  const style = edgeStyle(basis);
  const labelX = (sourceX + targetX) / 2;
  const labelY = (sourceY + targetY) / 2;
  const hasEvidence = (edge?.evidence_ids.length ?? 0) > 0;

  function openEvidence(): void {
    if (edge && hasEvidence) {
      evidenceDrawer.open(edge.evidence_ids);
    }
  }

  return (
    <g
      aria-label={hasEvidence ? "查看边证据" : undefined}
      data-testid={`edge-${id}`}
      onClick={openEvidence}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          openEvidence();
        }
      }}
      role={hasEvidence ? "button" : undefined}
      tabIndex={hasEvidence ? 0 : undefined}
    >
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
