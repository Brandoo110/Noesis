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
    <section aria-label="分类情报">
      <h2>分类情报流</h2>
      {items.length === 0 ? <p>暂无情报。</p> : null}
      <ul>
        {items.map((item) => (
          <li aria-label={`情报 ${item.title}`} key={item.title}>
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
