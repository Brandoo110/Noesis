import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, PositionRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.positions_repo import PositionsRepo
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
