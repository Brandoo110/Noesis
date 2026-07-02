import { PortfolioHome } from "../portfolio/PortfolioHome";
import type { GraphSeed } from "./view-types";

interface PortfolioViewProps {
  onGraphSeedSelected?: (seed: GraphSeed) => void;
}

export function PortfolioView({
  onGraphSeedSelected
}: PortfolioViewProps): JSX.Element {
  return (
    <section aria-label="组合首页">
      <PortfolioHome onGraphSeedSelected={onGraphSeedSelected} />
    </section>
  );
}
