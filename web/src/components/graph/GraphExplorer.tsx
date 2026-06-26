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

export interface GraphExplorerProps {
  positionId: string;
  seedEntity: EntityNode;
}

const NODE_TYPES: NodeTypes = {
  entity: EntityNodeView
};

const EDGE_TYPES: EdgeTypes = {
  edge: EdgeView
};

export function GraphExplorer({
  positionId,
  seedEntity
}: GraphExplorerProps): JSX.Element {
  const graph = useExpand({ positionId, seedEntity });

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
    </section>
  );
}
