from dataclasses import dataclass

from noesis.db.models import EntityRow, GraphEdgeRow
from noesis.graph.traversal import (
    CorrelationCell,
    CorrelationMatrix,
    MatrixAxis,
    SharedPosition,
    SharedSupplierGroup,
    shared_supply_chain,
    supply_chain_correlation,
)

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


def test_shared_supply_chain_groups_supplier_with_weakest_basis() -> None:
    edges = FakeEdgesRepo(
        [
            edge("entity-aapl", "entity-tsmc", basis="source_backed", confidence=0.91),
            edge("entity-msft", "entity-tsmc", basis="inferred", confidence=0.62),
        ]
    )
    entities = FakeEntitiesRepo(
        {"entity-tsmc": entity("entity-tsmc", "Taiwan Semiconductor", "TSM")}
    )

    groups = shared_supply_chain(
        [
            ("position-aapl", "AAPL", "entity-aapl"),
            ("position-msft", "MSFT", "entity-msft"),
        ],
        edges,
        entities,
    )

    assert groups == [
        SharedSupplierGroup(
            supplier_id="entity-tsmc",
            supplier_name="Taiwan Semiconductor",
            node_type="company",
            basis="inferred",
            positions=[
                SharedPosition("position-aapl", "AAPL", "entity-aapl", 0.91),
                SharedPosition("position-msft", "MSFT", "entity-msft", 0.62),
            ],
        )
    ]


def test_shared_supply_chain_ignores_single_or_missing_supplier_groups() -> None:
    groups = shared_supply_chain(
        [
            ("position-aapl", "AAPL", "entity-aapl"),
            ("position-msft", "MSFT", "entity-msft"),
        ],
        FakeEdgesRepo(
            [
                edge("entity-aapl", "entity-tsmc"),
                edge("entity-msft", "segment-ai", relation="belongs_to"),
            ]
        ),
        FakeEntitiesRepo({"entity-tsmc": entity("entity-tsmc", "TSMC", "TSM")}),
    )

    assert groups == []


def test_shared_supply_chain_sorts_and_handles_name_only_positions() -> None:
    edges = FakeEdgesRepo(
        [
            edge("entity-private", "entity-big", confidence=0.5),
            edge("entity-a", "entity-big", confidence=0.7),
            edge("entity-b", "entity-big", confidence=0.8),
            edge("entity-a", "entity-high", confidence=0.99),
            edge("entity-b", "entity-high", confidence=0.98),
        ]
    )
    entities = FakeEntitiesRepo(
        {
            "entity-big": entity("entity-big", "Big Supplier", "BIG"),
            "entity-high": entity("entity-high", "High Supplier", "HIGH"),
        }
    )

    groups = shared_supply_chain(
        [
            ("position-private", None, "entity-private"),
            ("position-a", "AAA", "entity-a"),
            ("position-b", "BBB", "entity-b"),
        ],
        edges,
        entities,
    )

    assert [group.supplier_id for group in groups] == ["entity-big", "entity-high"]
    assert groups[0].positions[0].symbol is None


def test_supply_chain_correlation_outputs_sparse_upper_triangle() -> None:
    edges = FakeEdgesRepo(
        [
            edge("entity-a", "entity-tsmc"),
            edge("entity-a", "entity-samsung"),
            edge("entity-b", "entity-tsmc"),
            edge("entity-b", "entity-samsung"),
            edge("entity-c", "entity-sony"),
        ]
    )
    entities = FakeEntitiesRepo(
        {
            "entity-tsmc": entity("entity-tsmc", "TSMC", "TSM"),
            "entity-samsung": entity("entity-samsung", "Samsung", "SSNLF"),
            "entity-sony": entity("entity-sony", "Sony", "SONY"),
        }
    )

    matrix = supply_chain_correlation(
        [
            ("position-a", "AAA", "entity-a"),
            ("position-b", "BBB", "entity-b"),
            ("position-c", "CCC", "entity-c"),
        ],
        edges,
        entities,
    )

    assert matrix == CorrelationMatrix(
        positions=[
            MatrixAxis("position-a", "AAA", "AAA"),
            MatrixAxis("position-b", "BBB", "BBB"),
            MatrixAxis("position-c", "CCC", "CCC"),
        ],
        cells=[
            CorrelationCell(
                a_position_id="position-a",
                b_position_id="position-b",
                shared_count=2,
                shared_suppliers=["Samsung", "TSMC"],
            )
        ],
    )


def test_supply_chain_correlation_returns_empty_cells_without_shared_suppliers() -> None:
    matrix = supply_chain_correlation(
        [
            ("position-a", "AAA", "entity-a"),
            ("position-b", "BBB", "entity-b"),
        ],
        FakeEdgesRepo(
            [
                edge("entity-a", "entity-tsmc"),
                edge("entity-b", "entity-samsung"),
            ]
        ),
    )

    assert matrix.cells == []


def edge(
    from_entity_id: str,
    to_entity_id: str,
    *,
    relation: str = "supplier",
    basis: str = "inferred",
    confidence: float = 0.7,
) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=f"edge-{from_entity_id}-{to_entity_id}",
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation=relation,
        basis=basis,
        confidence=confidence,
        evidence_ids_json="[]",
        run_id="run-1",
        rationale=None,
        created_at=NOW,
    )


def entity(
    id: str,
    name: str,
    symbol: str | None,
    node_type: str = "company",
) -> EntityRow:
    identifiers = "{}" if symbol is None else f'{{"symbol":"{symbol}"}}'
    aliases = "[]" if symbol is None else f'["{symbol}"]'
    return EntityRow(
        id=id,
        node_type=node_type,
        name=name,
        aliases_json=aliases,
        identifiers_json=identifiers,
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )
