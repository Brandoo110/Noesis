import type { StockDetailData, StockDetailErrors } from "../../hooks/use-stock-detail";

interface StatusSummaryProps {
  detail: StockDetailData;
  errors: StockDetailErrors;
}

export function StatusSummary({ detail, errors }: StatusSummaryProps): JSX.Element {
  const name = detail.entity?.name ?? detail.entityId;
  const summary = detail.thesis?.summary ?? `${name} 暂无综合 thesis。`;
  return (
    <section aria-label="现状" className="detail-section summary-section">
      <h2>现状一句话</h2>
      <p>{summary}</p>
      {Object.keys(errors).length > 0 ? (
        <small>{Object.values(errors).join(" / ")}</small>
      ) : null}
    </section>
  );
}
