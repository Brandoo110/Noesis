import type { StockDetailData } from "../../hooks/use-stock-detail";
import type { Edge, IntelItem, Thesis, ThesisAssumption } from "../../types/api";
import { downloadMarkdown, stockReportToMarkdown } from "../../lib/markdown";

interface StockReportProps {
  detail: StockDetailData;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

const RELATION_LABELS: Record<Edge["relation"], string> = {
  supplier: "供应商",
  customer: "客户",
  competitor: "竞品",
  belongs_to: "所属主题"
};

const KIND_LABELS: Record<ThesisAssumption["kind"], string> = {
  reason: "持有理由",
  assumption: "关键假设",
  risk: "风险"
};

export function StockReport({
  detail,
  onEvidenceClick
}: StockReportProps): JSX.Element {
  const symbol = detail.entity?.symbol ?? detail.entityId;

  function handleExport(): void {
    downloadMarkdown(`${symbol}-report.md`, stockReportToMarkdown(detail));
  }

  return (
    <section aria-label="个股深度报告">
      <header>
        <h2>{`${symbol} 深度报告`}</h2>
        <button onClick={handleExport} type="button">
          导出 Markdown
        </button>
      </header>
      <ReportSummary detail={detail} />
      <ReportChanges items={detail.intelItems} />
      <ReportChain edges={detail.neighbors} />
      <ReportIntel items={detail.intelItems} onEvidenceClick={onEvidenceClick} />
      <ReportSentiment items={detail.intelItems} />
      <ReportThesis thesis={detail.thesis} onEvidenceClick={onEvidenceClick} />
      <ReportAttention thesis={detail.thesis} onEvidenceClick={onEvidenceClick} />
      <ReportSources detail={detail} />
    </section>
  );
}

function ReportSummary({ detail }: { detail: StockDetailData }): JSX.Element {
  const name = detail.entity?.name ?? detail.entityId;
  return (
    <section>
      <h3>① 摘要</h3>
      <p>{detail.thesis?.summary ?? `${name} 暂无综合 thesis。`}</p>
    </section>
  );
}

function ReportChanges({ items }: { items: IntelItem[] }): JSX.Element {
  return (
    <section>
      <h3>② 变化</h3>
      {items.length === 0 ? <p>暂无变化情报。</p> : null}
      <ul>
        {items.map((item) => (
          <li key={item.title}>{`${item.title}: ${item.content}`}</li>
        ))}
      </ul>
    </section>
  );
}

function ReportChain({ edges }: { edges: Edge[] }): JSX.Element {
  return (
    <section>
      <h3>③ 产业链</h3>
      {edges.length === 0 ? <p>暂无产业链边。</p> : null}
      <ul>
        {edges.map((edge) => (
          <li key={edge.id}>
            <span>{RELATION_LABELS[edge.relation]}</span>
            <span>{edge.basis === "inferred" ? `${edge.to_name} (基于推断)` : edge.to_name}</span>
            <span>{`${Math.round(edge.confidence * 100)}%`}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReportIntel({
  items,
  onEvidenceClick
}: {
  items: IntelItem[];
  onEvidenceClick?: (evidenceIds: string[]) => void;
}): JSX.Element {
  return (
    <section>
      <h3>④ 分类情报</h3>
      {items.length === 0 ? <p>暂无情报。</p> : null}
      <ul>
        {items.map((item) => (
          <li aria-label={`报告情报 ${item.title}`} key={item.title}>
            <strong>{item.title}</strong>
            <span>{item.event_type}</span>
            <span>{item.sentiment.dir}</span>
            <span>{`tier ${item.source_tier}`}</span>
            <p>{item.content}</p>
            <button
              onClick={() => onEvidenceClick?.(item.evidence_ids)}
              type="button"
            >
              查看证据
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReportSentiment({ items }: { items: IntelItem[] }): JSX.Element {
  const counts = sentimentCounts(items);
  return (
    <section>
      <h3>⑤ 方向</h3>
      {items.length === 0 ? <p>暂无方向信号。</p> : null}
      <ul>
        <li>{`up: ${counts.up}`}</li>
        <li>{`down: ${counts.down}`}</li>
        <li>{`neutral: ${counts.neutral}`}</li>
      </ul>
    </section>
  );
}

function ReportThesis({
  thesis,
  onEvidenceClick
}: {
  thesis: Thesis | null;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}): JSX.Element {
  return (
    <section>
      <h3>⑥ Thesis</h3>
      {thesis ? <p>{thesis.summary}</p> : <p>暂无 thesis。</p>}
      {thesis ? (
        <ul>
          {thesis.assumptions.map((item) => (
            <li key={item.text}>
              <span>{`${KIND_LABELS[item.kind]}：${item.text}`}</span>
              <button
                onClick={() => onEvidenceClick?.(item.evidence_ids)}
                type="button"
              >
                查看证据
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ReportAttention({
  thesis,
  onEvidenceClick
}: {
  thesis: Thesis | null;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}): JSX.Element {
  const risks = thesis?.assumptions.filter((item) => item.kind === "risk") ?? [];
  return (
    <section>
      <h3>⑦ 关注点（仅供参考）</h3>
      <small>
        <strong>仅供参考</strong>
        {risks.length === 0 ? <span>暂无关注点。</span> : null}
        <ul>
          {risks.map((risk) => (
            <li key={risk.text}>
              <span>{risk.text}</span>
              <button
                onClick={() => onEvidenceClick?.(risk.evidence_ids)}
                type="button"
              >
                查看证据
              </button>
            </li>
          ))}
        </ul>
      </small>
    </section>
  );
}

function ReportSources({ detail }: { detail: StockDetailData }): JSX.Element {
  return (
    <section>
      <h3>⑧ 来源清单</h3>
      {detail.evidences.length === 0 ? <p>暂无来源。</p> : null}
      <ul>
        {detail.evidences.map((evidence) => (
          <li key={evidence.id}>
            <span>{evidence.title ?? evidence.id}</span>
            <span>{evidence.url ?? "无链接"}</span>
            <span>{`tier ${evidence.source_tier}`}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function sentimentCounts(items: IntelItem[]): { up: number; down: number; neutral: number } {
  return items.reduce(
    (current, item) => ({
      ...current,
      [item.sentiment.dir]: current[item.sentiment.dir] + 1
    }),
    { up: 0, down: 0, neutral: 0 }
  );
}
