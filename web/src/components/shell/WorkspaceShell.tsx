import { useMemo, useState } from "react";

import { AgentOpsView } from "../views/AgentOpsView";
import { GraphView } from "../views/GraphView";
import { PortfolioView } from "../views/PortfolioView";
import type { GraphSeed } from "../views/view-types";
import { MobileNav } from "./MobileNav";
import { SideRail } from "./SideRail";
import { WORKSPACE_VIEWS, type WorkspaceView } from "./shell-types";
import { TopBar } from "./TopBar";

export function WorkspaceShell(): JSX.Element {
  const [view, setView] = useState<WorkspaceView>("home");
  const [graphSeed, setGraphSeed] = useState<GraphSeed | null>(null);
  const graphSeedKey = graphSeed
    ? `${graphSeed.positionId}:${graphSeed.seedEntity.id}`
    : "empty";
  const meta = useMemo(
    () => WORKSPACE_VIEWS.find((item) => item.id === view) ?? WORKSPACE_VIEWS[0],
    [view]
  );

  function openGraph(seed: GraphSeed): void {
    setGraphSeed((current) => (sameGraphSeed(current, seed) ? current : seed));
    setView("graph");
  }

  return (
    <div className="noesis-app">
      <SideRail activeView={view} onViewChange={setView} />
      <div className="main-column">
        <TopBar
          showFilter={view === "home"}
          subtitle={meta.subtitle}
          title={meta.title}
        />
        <main className="page-body">
          {view === "home" ? <PortfolioView onGraphSeedSelected={openGraph} /> : null}
          <div hidden={view !== "graph"}>
            <GraphView key={graphSeedKey} seed={graphSeed} />
          </div>
          {view === "ops" ? <AgentOpsView /> : null}
        </main>
      </div>
      <MobileNav activeView={view} onViewChange={setView} />
    </div>
  );
}

function sameGraphSeed(current: GraphSeed | null, next: GraphSeed): boolean {
  return (
    current?.positionId === next.positionId &&
    current.seedEntity.id === next.seedEntity.id
  );
}
