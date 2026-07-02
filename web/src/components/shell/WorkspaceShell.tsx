import { useMemo, useState } from "react";

import { PortfolioView } from "../views/PortfolioView";
import { SideRail } from "./SideRail";
import { WORKSPACE_VIEWS, type WorkspaceView } from "./shell-types";
import { TopBar } from "./TopBar";

export function WorkspaceShell(): JSX.Element {
  const [view, setView] = useState<WorkspaceView>("home");
  const meta = useMemo(
    () => WORKSPACE_VIEWS.find((item) => item.id === view) ?? WORKSPACE_VIEWS[0],
    [view]
  );

  return (
    <div className="noesis-app">
      <SideRail activeView={view} onViewChange={setView} />
      <div className="main-column">
        <TopBar subtitle={meta.subtitle} title={meta.title} />
        <main className="page-body">
          {view === "home" ? <PortfolioView /> : null}
          {view === "graph" ? <DeferredView label="图谱探索" phase="P2" /> : null}
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
