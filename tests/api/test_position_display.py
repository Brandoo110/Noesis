import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, PositionRow, RunRow, ThesisRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.theses_repo import ThesesRepo
from tests.api.conftest import ApiTestContext, NOW


def test_list_positions_uses_latest_entity_for_display_label(
    api_context: ApiTestContext,
) -> None:
    _seed_resolved_tesla(api_context)

    response = api_context.client.get("/positions")
    payload = response.json()

    assert response.status_code == 200
    assert payload[0]["symbol"] == "TSLA"
    assert payload[0]["name"] == "Tesla Inc."


def test_portfolio_brief_uses_latest_entity_for_position_label(
    api_context: ApiTestContext,
) -> None:
    _seed_resolved_tesla(api_context)

    response = api_context.client.get("/portfolio/brief")
    payload = response.json()

    assert response.status_code == 200
    assert payload["positions"][0]["symbol"] == "TSLA"
    assert payload["positions"][0]["name"] == "Tesla Inc."


def _seed_resolved_tesla(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            EntitiesRepo().upsert(_entity(), conn=conn)
            PositionsRepo().insert(_position(), conn=conn)
            RunRegistryRepo().insert(_run(), conn=conn)
            ThesesRepo().insert(_thesis(), conn=conn)
    finally:
        conn.close()


def _entity() -> EntityRow:
    return EntityRow(
        id="entity-tsla",
        node_type="company",
        name="Tesla Inc.",
        aliases_json=json.dumps(["Tesla"]),
        identifiers_json=json.dumps({"symbol": "TSLA"}),
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def _position() -> PositionRow:
    return PositionRow(
        id="position-tesla",
        user_id="local-user",
        symbol="tesla",
        market="US",
        name=None,
        kind="owned",
        qty=None,
        cost_basis=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _run() -> RunRow:
    return RunRow(
        id="run-tsla",
        position_id="position-tesla",
        entity_id="entity-tsla",
        node_kind="seed",
        status="completed",
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )


def _thesis() -> ThesisRow:
    return ThesisRow(
        id="thesis-tsla",
        position_id="position-tesla",
        run_id="run-tsla",
        summary="Tesla supply chain context is evidence-backed.",
        status="confirmed",
        created_at=NOW,
        updated_at=NOW,
    )
