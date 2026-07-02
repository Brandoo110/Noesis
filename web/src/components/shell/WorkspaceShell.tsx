import { useMemo, useState } from "react";

import { GraphView } from "../views/GraphView";
import { PortfolioView } from "../views/PortfolioView";
import type { GraphSeed } from "../views/view-types";
import { SideRail } from "./SideRail";
import { WORKSPACE_VIEWS, type WorkspaceView } from "./shell-types";
import { TopBar } from "./TopBar";

export function WorkspaceShell(): JSX.Element {
  const [view, setView] = useState<WorkspaceView>("home");
  const [graphSeed, setGraphSeed] = useState<GraphSeed | null>(null);
  const meta = useMemo(
    () => WORKSPACE_VIEWS.find((item) => item.id === view) ?? WORKSPACE_VIEWS[0],
    [view]
  );

  function openGraph(seed: GraphSeed): void {
    setGraphSeed(seed);
    setView("graph");
  }

  return (
    <div className="noesis-app">
      <SideRail activeView={view} onViewChange={setView} />
      <div className="main-column">
        <TopBar subtitle={meta.subtitle} title={meta.title} />
        <main className="page-body">
          {view === "home" ? <PortfolioView onGraphSeedSelected={openGraph} /> : null}
          {view === "graph" ? <GraphView seed={graphSeed} /> : null}
          {view === "ops" ? <DeferredView label="AgentOps" phase="P3" /> : null}
        </main>
      </div>
    </div>
  );
}

function DeferredView({
  label,
  phase
}: {
  label: string;
  phase: "P2" | "P3";
}): JSX.Element {
  return (
    <section aria-label={`${label}视图`} className="surface placeholder-surface">
      <p className="eyebrow">V1.7 {phase}</p>
      <h2>{label}</h2>
      <p className="muted">
        <strong>仅供参考</strong>
        <span>。该视图将在后续 Phase 接回真实数据流。</span>
      </p>
    </section>
  );
}
