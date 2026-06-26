import { useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  type EdgeTypes,
  type NodeTypes
} from "reactflow";
import "reactflow/dist/style.css";

import { useExpand } from "../../hooks/use-expand";
import type { EntityNode } from "../../types/api";
import { EdgeView } from "./EdgeView";
import { EntityNodeView } from "./EntityNodeView";
import { StockDetail } from "../stock/StockDetail";

export interface GraphExplorerProps {
  positionId: string;
  seedEntity: EntityNode;
  runId?: string;
}

const NODE_TYPES: NodeTypes = {
  entity: EntityNodeView
};

const EDGE_TYPES: EdgeTypes = {
  edge: EdgeView
};

export function GraphExplorer({
  positionId,
  runId,
  seedEntity
}: GraphExplorerProps): JSX.Element {
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const graph = useExpand({
    onViewDetail: runId ? () => setIsDetailOpen(true) : undefined,
    positionId,
    seedEntity
  });

  return (
    <section aria-label="图谱探索器">
      <ReactFlowProvider>
        <div style={{ height: 520, width: "100%" }}>
          <ReactFlow
            edgeTypes={EDGE_TYPES}
            edges={graph.edges}
            fitView
            nodeTypes={NODE_TYPES}
            nodes={graph.nodes}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>
      </ReactFlowProvider>
      {isDetailOpen && runId ? (
        <StockDetail
          entityId={seedEntity.id}
          positionId={positionId}
          runId={runId}
        />
      ) : null}
    </section>
  );
}
