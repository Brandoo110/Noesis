export function PortfolioMobileTabbar(): JSX.Element {
  return (
    <nav aria-label="移动端导航" className="mobile-tabbar">
      <a href="#portfolio-title">
        <span aria-hidden="true">I</span>
        <strong>Intelligence</strong>
      </a>
      <a aria-current="page" href="#portfolio-title">
        <span aria-hidden="true">P</span>
        <strong>Portfolio</strong>
      </a>
      <a href="#positions">
        <span aria-hidden="true">W</span>
        <strong>Positions</strong>
      </a>
      <a href="#research-workspace">
        <span aria-hidden="true">R</span>
        <strong>Research</strong>
      </a>
      <a href="#portfolio-brief">
        <span aria-hidden="true">A</span>
        <strong>Analytics</strong>
      </a>
    </nav>
  );
}
