from dataclasses import dataclass

from noesis.db.models import GraphEdgeRow
from noesis.graph.traversal import relevance_path

NOW = "2026-06-26T00:00:00Z"


@dataclass
class FakeEdgesRepo:
    edges: list[GraphEdgeRow]

    def list_from(self, entity_id: str) -> list[GraphEdgeRow]:
        return [edge for edge in self.edges if edge.from_entity_id == entity_id]


def test_relevance_path_returns_path_to_seed_entity() -> None:
    repo = FakeEdgesRepo(
        [
            edge("entity-a", "entity-b"),
            edge("entity-b", "entity-seed"),
        ]
    )

    path = relevance_path("entity-a", "entity-seed", repo)

    assert path == ["entity-a", "entity-b", "entity-seed"]


def test_relevance_path_returns_none_when_disconnected() -> None:
    repo = FakeEdgesRepo([edge("entity-a", "entity-b")])

    path = relevance_path("entity-a", "entity-seed", repo)

    assert path is None


def test_relevance_path_chooses_shortest_path() -> None:
    repo = FakeEdgesRepo(
        [
            edge("entity-a", "entity-b"),
            edge("entity-b", "entity-c"),
            edge("entity-c", "entity-seed"),
            edge("entity-a", "entity-seed"),
        ]
    )

    path = relevance_path("entity-a", "entity-seed", repo)

    assert path == ["entity-a", "entity-seed"]


def edge(from_entity_id: str, to_entity_id: str, confidence: float = 0.7) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=f"edge-{from_entity_id}-{to_entity_id}",
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation="supplier",
        basis="inferred",
        confidence=confidence,
        evidence_ids_json="[]",
        run_id="run-1",
        rationale=None,
        created_at=NOW,
    )
