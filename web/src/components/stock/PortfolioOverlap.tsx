import type { Basis, OverlapGroup, OverlapPosition } from "../../types/api";

interface PortfolioOverlapProps {
  entityId: string;
  overlaps: OverlapGroup[];
}

export function PortfolioOverlap({
  entityId,
  overlaps
}: PortfolioOverlapProps): JSX.Element {
  const groups = overlaps
    .map((group) => ({
      group,
      others: otherPositions(group.positions, entityId)
    }))
    .filter(({ group, others }) =>
      group.positions.some((position) => position.entity_id === entityId) &&
      others.length > 0
    );

  return (
    <section aria-label="和其他持仓的关系" className="watch-card">
      <h2>和其他持仓的关系</h2>
      <small aria-label="组合重叠关系">
        <strong>仅供参考</strong>
        {groups.length === 0 ? (
          <span>与其他持仓无产业段重叠</span>
        ) : (
          <ul>
            {groups.map(({ group, others }) => (
              <li key={group.segment_id}>
                <strong>{group.segment_name}</strong>
                <span>{others.map((position) => position.symbol).join(" / ")}</span>
                <span className={`basis-badge ${group.basis}`}>
                  {basisLabel(group.basis)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </small>
    </section>
  );
}

function otherPositions(
  positions: OverlapPosition[],
  entityId: string
): OverlapPosition[] {
  return positions.filter((position) => position.entity_id !== entityId);
}

function basisLabel(basis: Basis): string {
  return basis === "source_backed" ? "有出处" : "基于推断";
}
