import type { EntityNode } from "../../types/api";

interface PositionRelationProps {
  path: EntityNode[];
}

export function PositionRelation({ path }: PositionRelationProps): JSX.Element {
  return (
    <section aria-label="持仓关系" className="watch-card">
      <h2>和持仓关系</h2>
      {path.length === 0 ? <p>暂无路径。</p> : <p>{formatPath(path)}</p>}
    </section>
  );
}

function formatPath(path: EntityNode[]): string {
  return path.map((item) => item.name).join(" / ");
}
