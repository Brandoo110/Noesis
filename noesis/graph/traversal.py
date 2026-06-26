from collections import deque
from typing import Protocol

from noesis.db.models import GraphEdgeRow


class EdgesReader(Protocol):
    def list_from(self, entity_id: str) -> list[GraphEdgeRow]: ...


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
