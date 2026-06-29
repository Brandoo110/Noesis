import { EvidenceDrawer } from "./components/evidence/EvidenceDrawer";
import { PortfolioHome } from "./components/portfolio/PortfolioHome";
import { EvidenceDrawerProvider } from "./context/evidence-drawer";

export function App(): JSX.Element {
  return (
    <EvidenceDrawerProvider>
      <main className="app-shell">
        <PortfolioHome />
      </main>
      <EvidenceDrawer />
    </EvidenceDrawerProvider>
  );
}
