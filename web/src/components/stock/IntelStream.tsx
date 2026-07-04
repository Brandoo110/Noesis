import type { IntelItem } from "../../types/api";

interface IntelStreamProps {
  items: IntelItem[];
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

const SENTIMENT_LABELS: Record<IntelItem["sentiment"]["dir"], string> = {
  up: "正向",
  down: "负向",
  neutral: "中性"
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  supply_chain: "供应链",
  demand: "需求",
  product: "产品",
  partnership: "合作",
  financial: "财务",
  legal: "监管",
  risk: "风险"
};

export function IntelStream({
  items,
  onEvidenceClick
}: IntelStreamProps): JSX.Element {
  return (
    <section aria-label="分类情报" className="intel-list">
      <h2>分类情报流</h2>
      {items.length === 0 ? <p className="empty-note">暂无情报。</p> : null}
      <ul>
        {items.map((item) => (
          <li aria-label={`情报 ${item.title}`} key={item.title}>
            <div>
              <strong>{item.title}</strong>
              <span>{eventTypeLabel(item.event_type)}</span>
            </div>
            <div>
              <span>{SENTIMENT_LABELS[item.sentiment.dir]}</span>
              <span>{`tier ${item.source_tier}`}</span>
            </div>
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

function eventTypeLabel(eventType: string): string {
  return EVENT_TYPE_LABELS[eventType] ?? eventType;
}
