import type { Edge } from "../../types/api";

const RELATION_LABELS: Record<Edge["relation"], string> = {
  supplier: "供应商",
  customer: "客户",
  competitor: "竞品",
  belongs_to: "所属主题"
};

interface ChainMiniProps {
  edges: Edge[];
}

export function ChainMini({ edges }: ChainMiniProps): JSX.Element {
  return (
    <section aria-label="产业链位置" className="detail-section chain-section">
      <h2>产业链位置</h2>
      {edges.length === 0 ? <p>暂无产业链边。</p> : null}
      <ul className="chain-list">
        {edges.map((edge) => (
          <li key={edge.id}>
            <span>{RELATION_LABELS[edge.relation]}</span>
            <span>{edge.to_name}</span>
            <span>{edge.basis}</span>
            <span>{Math.round(edge.confidence * 100)}%</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
