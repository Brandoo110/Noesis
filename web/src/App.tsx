import { EvidenceDrawer } from "./components/evidence/EvidenceDrawer";
import { WorkspaceShell } from "./components/shell/WorkspaceShell";
import { EvidenceDrawerProvider } from "./context/evidence-drawer";

export function App(): JSX.Element {
  return (
    <EvidenceDrawerProvider>
      <WorkspaceShell />
      <EvidenceDrawer />
    </EvidenceDrawerProvider>
  );
}
