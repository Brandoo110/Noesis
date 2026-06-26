from dataclasses import dataclass

from noesis.db.models import EntityRow
from noesis.db.models import GraphEdgeRow
from noesis.graph.traversal import EntityRef, relevance_path, representative_stocks

NOW = "2026-06-26T00:00:00Z"


@dataclass
class FakeEdgesRepo:
    edges: list[GraphEdgeRow]

    def list_from(self, entity_id: str) -> list[GraphEdgeRow]:
        return [edge for edge in self.edges if edge.from_entity_id == entity_id]

    def list_to(self, entity_id: str) -> list[GraphEdgeRow]:
        return [edge for edge in self.edges if edge.to_entity_id == entity_id]


@dataclass
class FakeEntitiesRepo:
    rows: dict[str, EntityRow]

    def get(self, id: str) -> EntityRow | None:
        return self.rows.get(id)


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


def test_representative_stocks_returns_belongs_to_companies_sorted() -> None:
    edges = FakeEdgesRepo(
        [
            edge("entity-low", "segment-ai", relation="belongs_to", confidence=0.4),
            edge("entity-high", "segment-ai", relation="belongs_to", confidence=0.9),
            edge("entity-mid", "segment-ai", relation="belongs_to", confidence=0.7),
            edge("entity-other", "segment-ai", relation="supplier", confidence=1.0),
        ]
    )
    entities = FakeEntitiesRepo(
        {
            "entity-low": entity("entity-low", "Low Corp", "LOW"),
            "entity-mid": entity("entity-mid", "Mid Corp", "MID"),
            "entity-high": entity("entity-high", "High Corp", "HIGH"),
            "entity-other": entity("entity-other", "Other Corp", "OTHER"),
        }
    )

    stocks = representative_stocks("segment-ai", edges, entities, top_n=2)

    assert stocks == [
        EntityRef(id="entity-high", name="High Corp", symbol="HIGH"),
        EntityRef(id="entity-mid", name="Mid Corp", symbol="MID"),
    ]


def test_representative_stocks_returns_empty_for_empty_segment() -> None:
    stocks = representative_stocks(
        "segment-empty",
        FakeEdgesRepo([]),
        FakeEntitiesRepo({}),
    )

    assert stocks == []


def edge(
    from_entity_id: str,
    to_entity_id: str,
    *,
    relation: str = "supplier",
    confidence: float = 0.7,
) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=f"edge-{from_entity_id}-{to_entity_id}",
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation=relation,
        basis="inferred",
        confidence=confidence,
        evidence_ids_json="[]",
        run_id="run-1",
        rationale=None,
        created_at=NOW,
    )


def entity(id: str, name: str, symbol: str) -> EntityRow:
    return EntityRow(
        id=id,
        node_type="company",
        name=name,
        aliases_json=f'["{symbol}"]',
        identifiers_json=f'{{"symbol":"{symbol}"}}',
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )
