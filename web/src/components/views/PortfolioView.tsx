import { PortfolioHome } from "../portfolio/PortfolioHome";

export function PortfolioView(): JSX.Element {
  return (
    <section aria-label="组合首页" className="portfolio-view">
      <PortfolioHome />
    </section>
  );
}
