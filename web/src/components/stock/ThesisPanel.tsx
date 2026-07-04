import type { ConfirmationInput, Thesis, ThesisAssumption } from "../../types/api";

interface ThesisPanelProps {
  thesis: Thesis | null;
  onConfirm: (status: ConfirmationInput["status"]) => void;
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

const KIND_LABELS: Record<ThesisAssumption["kind"], string> = {
  reason: "持有理由",
  assumption: "关键假设",
  risk: "风险"
};

export function ThesisPanel({
  thesis,
  onConfirm,
  onEvidenceClick
}: ThesisPanelProps): JSX.Element {
  return (
    <section aria-label="研究假设" className="thesis-groups">
      <h2>研究假设</h2>
      {thesis ? <p>{thesis.summary}</p> : <p className="empty-note">暂无研究假设。</p>}
      {thesis ? (
        <>
          {(["reason", "assumption", "risk"] as const).map((kind) => (
            <AssumptionGroup
              assumptions={thesis.assumptions.filter((item) => item.kind === kind)}
              key={kind}
              kind={kind}
              onEvidenceClick={onEvidenceClick}
            />
          ))}
          <div className="confirm-row">
            <button className="primary-button" onClick={() => onConfirm("confirmed")} type="button">
              确认研究假设
            </button>
            <button onClick={() => onConfirm("edited")} type="button">
              标记需修改
            </button>
            <button onClick={() => onConfirm("rejected")} type="button">
              拒绝研究假设
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

interface AssumptionGroupProps {
  kind: ThesisAssumption["kind"];
  assumptions: ThesisAssumption[];
  onEvidenceClick?: (evidenceIds: string[]) => void;
}

function AssumptionGroup({
  kind,
  assumptions,
  onEvidenceClick
}: AssumptionGroupProps): JSX.Element {
  return (
    <section aria-label={KIND_LABELS[kind]} className={`thesis-group ${groupColor(kind)}`}>
      <h3>{KIND_LABELS[kind]}</h3>
      {assumptions.length === 0 ? <p className="empty-note">暂无。</p> : null}
      <ul>
        {assumptions.map((assumption) => (
          <li key={assumption.text}>
            <span>{assumption.text}</span>
            <button
              onClick={() => onEvidenceClick?.(assumption.evidence_ids)}
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

function groupColor(kind: ThesisAssumption["kind"]): "green" | "blue" | "amber" {
  if (kind === "reason") return "green";
  if (kind === "assumption") return "blue";
  return "amber";
}
