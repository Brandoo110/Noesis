import type { CSSProperties } from "react";

import type { Basis, NodeType } from "../types/api";

interface NodeVisual {
  className: string;
  style: CSSProperties;
}

interface EdgeVisual {
  className: string;
  style: CSSProperties;
}

export const NODE_VISUALS: Record<NodeType, NodeVisual> = {
  company: {
    className: "node-company",
    style: {
      backgroundColor: "#f8fafc",
      borderColor: "#2563eb",
      color: "#0f172a"
    }
  },
  segment: {
    className: "node-segment",
    style: {
      backgroundColor: "#fef3c7",
      borderColor: "#d97706",
      color: "#431407"
    }
  },
  theme: {
    className: "node-theme",
    style: {
      backgroundColor: "#ecfdf5",
      borderColor: "#059669",
      color: "#052e16"
    }
  }
};

export const SEED_NODE_VISUAL: NodeVisual = {
  className: "node-seed",
  style: {
    borderColor: "#111827",
    borderWidth: "2px",
    boxShadow: "0 0 0 3px rgba(17, 24, 39, 0.12)"
  }
};

export const EDGE_VISUALS: Record<Basis, EdgeVisual> = {
  source_backed: {
    className: "edge-source-backed",
    style: {
      opacity: 1,
      stroke: "#0f766e",
      strokeDasharray: "none",
      strokeWidth: 2
    }
  },
  inferred: {
    className: "edge-inferred",
    style: {
      opacity: 0.55,
      stroke: "#64748b",
      strokeDasharray: "6 4",
      strokeWidth: 2
    }
  }
};

export function nodeClassName(nodeType: NodeType, isSeed: boolean): string {
  const base = NODE_VISUALS[nodeType].className;
  return isSeed ? `${base} ${SEED_NODE_VISUAL.className}` : base;
}

export function nodeStyle(nodeType: NodeType, isSeed: boolean): CSSProperties {
  return {
    ...NODE_VISUALS[nodeType].style,
    ...(isSeed ? SEED_NODE_VISUAL.style : {}),
    borderStyle: "solid",
    borderRadius: "8px"
  };
}

export function edgeClassName(basis: Basis): string {
  return EDGE_VISUALS[basis].className;
}

export function edgeStyle(basis: Basis): CSSProperties {
  return EDGE_VISUALS[basis].style;
}
