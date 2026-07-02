import type { RefObject } from "react";

import { GraphExplorer } from "../graph/GraphExplorer";
import type { GraphSeed } from "../views/view-types";

interface PortfolioGraphWorkspaceProps {
  graphSeed: GraphSeed | null;
  onRetryResearch: (positionId: string) => Promise<void>;
  onThesisConfirmed: () => Promise<void>;
  workspaceRef: RefObject<HTMLElement>;
}

export function PortfolioGraphWorkspace({
  graphSeed,
  onRetryResearch,
  onThesisConfirmed,
  workspaceRef
}: PortfolioGraphWorkspaceProps): JSX.Element {
  return (
    <section
      aria-label="研究工作区"
      className="card graph-summary"
      id="research-workspace"
      ref={workspaceRef}
      tabIndex={-1}
    >
      {graphSeed ? (
        <GraphExplorer
          onThesisConfirmed={() => void onThesisConfirmed()}
          onRetryResearch={onRetryResearch}
          positionId={graphSeed.positionId}
          runId={graphSeed.runId}
          seedEntity={graphSeed.seedEntity}
        />
      ) : (
        <div className="empty-box">
          <p className="eyebrow">图谱探索器</p>
          <h2>选择一个完成研究的持仓查看图谱</h2>
          <p>
            点击“开始研究”，等待 run 进入待确认或完成状态后，打开产业链图谱和个股详情。
          </p>
        </div>
      )}
    </section>
  );
}
