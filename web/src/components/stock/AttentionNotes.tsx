import type { Thesis } from "../../types/api";

interface AttentionNotesProps {
  thesis: Thesis | null;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

export function AttentionNotes({
  thesis,
  onEvidenceClick
}: AttentionNotesProps): JSX.Element {
  const risks = thesis?.assumptions.filter((item) => item.kind === "risk") ?? [];
  return (
    <section aria-label="关注点" className="watch-card">
      <h2>关注点</h2>
      <small aria-label="关注点列表">
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
