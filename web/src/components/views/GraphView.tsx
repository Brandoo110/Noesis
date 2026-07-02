import { GraphExplorer } from "../graph/GraphExplorer";
import type { GraphSeed } from "./view-types";

interface GraphViewProps {
  seed: GraphSeed | null;
}

export function GraphView({ seed }: GraphViewProps): JSX.Element {
  if (!seed) {
    return (
      <section aria-label="图谱探索视图" className="graph-view empty-box">
        <p className="eyebrow">Research Graph</p>
        <h2>选择一个持仓进入图谱</h2>
        <p>从组合工作台选择已完成研究的持仓后，这里会显示真实图谱与证据关系。</p>
      </section>
    );
  }

  return (
    <section aria-label="图谱探索视图" className="graph-view">
      <GraphExplorer
        positionId={seed.positionId}
        runId={seed.runId}
        seedEntity={seed.seedEntity}
      />
    </section>
  );
}
