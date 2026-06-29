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
      backgroundColor: "#ffffff",
      borderColor: "#9fbac9",
      color: "#233f50"
    }
  },
  segment: {
    className: "node-segment",
    style: {
      backgroundColor: "#ffffff",
      borderColor: "#a6c892",
      color: "#334b2a"
    }
  },
  theme: {
    className: "node-theme",
    style: {
      backgroundColor: "#ffffff",
      borderColor: "#d9ad73",
      color: "#67471f"
    }
  }
};

export const SEED_NODE_VISUAL: NodeVisual = {
  className: "node-seed",
  style: {
    backgroundColor: "#ffffff",
    borderColor: "#005155",
    borderWidth: "2px",
    boxShadow: "0 2px 10px rgba(0, 81, 85, 0.14)",
    color: "#005155"
  }
};

export const EDGE_VISUALS: Record<Basis, EdgeVisual> = {
  source_backed: {
    className: "edge-source-backed",
    style: {
      opacity: 0.88,
      stroke: "#005155",
      strokeDasharray: "none",
      strokeWidth: 2
    }
  },
  inferred: {
    className: "edge-inferred",
    style: {
      opacity: 0.5,
      stroke: "#bec9c9",
      strokeDasharray: "4 4",
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
