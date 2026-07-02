import { AgentOpsDashboard } from "../agentops/AgentOpsDashboard";

export function AgentOpsView(): JSX.Element {
  return (
    <section aria-label="AgentOps视图" className="ops-view">
      <AgentOpsDashboard />
    </section>
  );
}
