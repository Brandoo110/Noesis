import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, GraphEdgeRow, PositionRow, RunRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from tests.api.conftest import ApiTestContext, NOW


def test_expand_entity_returns_edges_and_cache_hit(
    api_context: ApiTestContext,
) -> None:
    _seed_position_and_entity(api_context)

    first = api_context.client.post(
        "/entities/entity-aapl/expand",
        json={"position_id": "position-1"},
    )
    second = api_context.client.post(
        "/entities/entity-aapl/expand",
        json={"position_id": "position-1"},
    )

    first_payload = first.json()
    second_payload = second.json()

    assert first.status_code == 200
    assert first_payload["status"] == "completed"
    assert first_payload["entity_id"] == "entity-aapl"
    assert len(first_payload["edges"]) == 1
    edge = first_payload["edges"][0]
    assert edge["to_name"] == "Taiwan Semiconductor Manufacturing"
    assert edge["to_symbol"] == "TSM"
    assert edge["relation"] == "supplier"
    assert edge["basis"] == "source_backed"
    assert edge["confidence"] == 0.82
    assert edge["evidence_ids"]
    assert edge["source_tier"] == 2
    assert edge["neighbor"]["id"].startswith("entity-company-us-tsm")

    assert second.status_code == 200
    assert second_payload["status"] == "cached"
    assert second_payload["edges"][0]["evidence_ids"] == edge["evidence_ids"]


def test_neighbors_returns_edges_with_neighbor_payload(
    api_context: ApiTestContext,
) -> None:
    _seed_position_and_entity(api_context)
    api_context.client.post(
        "/entities/entity-aapl/expand",
        json={"position_id": "position-1"},
    )

    response = api_context.client.get("/entities/entity-aapl/neighbors")
    payload = response.json()

    assert response.status_code == 200
    assert payload["entity_id"] == "entity-aapl"
    assert payload["edges"][0]["to_symbol"] == "TSM"
    assert payload["edges"][0]["basis"] == "source_backed"
    assert payload["edges"][0]["source_tier"] == 2
    assert payload["edges"][0]["neighbor"]["name"] == "Taiwan Semiconductor Manufacturing"


def test_neighbors_returns_empty_result(api_context: ApiTestContext) -> None:
    _seed_position_and_entity(api_context)

    response = api_context.client.get("/entities/entity-aapl/neighbors")

    assert response.status_code == 200
    assert response.json()["edges"] == []


def test_relevance_returns_path_to_position_seed(
    api_context: ApiTestContext,
) -> None:
    _seed_relevance_graph(api_context)

    response = api_context.client.get(
        "/entities/entity-supplier/relevance",
        params={"position_id": "position-1"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert [item["id"] for item in payload["path"]] == [
        "entity-supplier",
        "entity-tier1",
        "entity-seed",
    ]
    assert payload["path"][2]["name"] == "Apple Inc."


def test_relevance_returns_empty_path(api_context: ApiTestContext) -> None:
    _seed_position_and_entity(api_context)

    response = api_context.client.get(
        "/entities/entity-aapl/relevance",
        params={"position_id": "position-1"},
    )

    assert response.status_code == 200
    assert response.json()["path"] == []


def _seed_position_and_entity(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            PositionsRepo().insert(
                PositionRow(
                    id="position-1",
                    user_id="local-user",
                    symbol="AAPL",
                    market="US",
                    name="Apple",
                    kind="owned",
                    qty=10,
                    cost_basis=150,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
            EntitiesRepo().upsert(
                EntityRow(
                    id="entity-aapl",
                    node_type="company",
                    name="Apple Inc.",
                    aliases_json=json.dumps(["AAPL"]),
                    identifiers_json=json.dumps({"symbol": "AAPL"}),
                    market="US",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
    finally:
        conn.close()


def _seed_relevance_graph(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            PositionsRepo().insert(
                PositionRow(
                    id="position-1",
                    user_id="local-user",
                    symbol="AAPL",
                    market="US",
                    name="Apple",
                    kind="owned",
                    qty=None,
                    cost_basis=None,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
            entities = EntitiesRepo()
            entities.upsert(_entity("entity-seed", "Apple Inc.", "AAPL"), conn=conn)
            entities.upsert(_entity("entity-tier1", "Tier One Supplier", "TIER"), conn=conn)
            entities.upsert(_entity("entity-supplier", "Supplier", "SUP"), conn=conn)
            RunRegistryRepo().insert(
                RunRow(
                    id="run-seed",
                    position_id="position-1",
                    entity_id="entity-seed",
                    node_kind="seed",
                    status="completed",
                    started_at=NOW,
                    ended_at=NOW,
                    created_at=NOW,
                ),
                conn=conn,
            )
            GraphEdgesRepo().insert_many(
                [
                    _edge("edge-supplier-tier1", "entity-supplier", "entity-tier1"),
                    _edge("edge-tier1-seed", "entity-tier1", "entity-seed"),
                ],
                conn=conn,
            )
    finally:
        conn.close()


def _entity(id: str, name: str, symbol: str) -> EntityRow:
    return EntityRow(
        id=id,
        node_type="company",
        name=name,
        aliases_json=json.dumps([symbol]),
        identifiers_json=json.dumps({"symbol": symbol}),
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def _edge(id: str, from_entity_id: str, to_entity_id: str) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=id,
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation="supplier",
        basis="inferred",
        confidence=0.7,
        evidence_ids_json=json.dumps([]),
        run_id="run-seed",
        rationale="Direct supply-chain link.",
        created_at=NOW,
    )
