from collections import deque
from dataclasses import dataclass
from typing import Protocol

from noesis.db.models import EntityRow, GraphEdgeRow


class EdgesReader(Protocol):
    def list_from(self, entity_id: str) -> list[GraphEdgeRow]: ...

    def list_to(self, entity_id: str) -> list[GraphEdgeRow]: ...


class EntitiesReader(Protocol):
    def get(self, id: str) -> EntityRow | None: ...


@dataclass(frozen=True)
class EntityRef:
    id: str
    name: str
    symbol: str | None


def relevance_path(
    entity_id: str,
    position_id: str,
    edges_repo: EdgesReader,
    *,
    max_depth: int = 3,
) -> list[str] | None:
    if entity_id == position_id:
        return [entity_id]
    queue: deque[tuple[str, list[str]]] = deque([(entity_id, [entity_id])])
    visited = {entity_id}
    while queue:
        current_id, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        for edge in edges_repo.list_from(current_id):
            next_id = edge.to_entity_id
            if next_id in visited:
                continue
            next_path = [*path, next_id]
            if next_id == position_id:
                return next_path
            visited.add(next_id)
            queue.append((next_id, next_path))
    return None


def representative_stocks(
    segment_entity_id: str,
    edges_repo: EdgesReader,
    entities_repo: EntitiesReader,
    *,
    top_n: int = 5,
) -> list[EntityRef]:
    belongs_to_edges = [
        edge
        for edge in edges_repo.list_to(segment_entity_id)
        if edge.relation == "belongs_to"
    ]
    sorted_edges = sorted(
        belongs_to_edges,
        key=lambda edge: edge.confidence,
        reverse=True,
    )
    refs: list[EntityRef] = []
    for edge in sorted_edges[:top_n]:
        row = entities_repo.get(edge.from_entity_id)
        if row is None or row.node_type != "company":
            continue
        refs.append(
            EntityRef(
                id=row.id,
                name=row.name,
                symbol=row.identifiers().get("symbol"),
            )
        )
    return refs
