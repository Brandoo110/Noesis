import type { IntelItem } from "../../types/api";

interface IntelStreamProps {
  items: IntelItem[];
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

export function IntelStream({
  items,
  onEvidenceClick
}: IntelStreamProps): JSX.Element {
  return (
    <section aria-label="分类情报" className="detail-section">
      <h2>分类情报流</h2>
      {items.length === 0 ? <p className="empty-note">暂无情报。</p> : null}
      <ul className="intel-list">
        {items.map((item) => (
          <li aria-label={`情报 ${item.title}`} key={item.title}>
            <div className="item-heading">
              <strong>{item.title}</strong>
              <span>{item.event_type}</span>
            </div>
            <div className="meta-row">
              <span>{item.sentiment.dir}</span>
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
