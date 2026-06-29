from noesis.db.connection import connect, with_tx

from tests.api.conftest import ApiTestContext


def test_create_position_returns_explicit_response(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/positions",
        json={
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple",
            "kind": "owned",
            "qty": 10,
            "cost_basis": 150,
        },
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["id"].startswith("position-")
    assert payload["symbol"] == "AAPL"
    assert payload["market"] == "US"
    assert payload["kind"] == "owned"
    assert payload["qty"] == 10


def test_create_position_rejects_missing_symbol(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/positions",
        json={
            "market": "US",
            "kind": "owned",
        },
    )

    assert response.status_code == 422


def test_create_position_reuses_existing_symbol_market_kind(
    api_context: ApiTestContext,
) -> None:
    first = api_context.client.post(
        "/positions",
        json={
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple",
            "kind": "owned",
        },
    )
    duplicate = api_context.client.post(
        "/positions",
        json={
            "symbol": "aapl",
            "market": "us",
            "name": "Apple duplicate",
            "kind": "owned",
        },
    )

    response = api_context.client.get("/positions")

    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == first.json()["id"]
    assert [item["symbol"] for item in response.json()] == ["AAPL"]


def test_create_position_accepts_company_name_without_symbol(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/positions",
        json={
            "market": "US",
            "name": "SpaceX",
            "kind": "watching",
        },
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["symbol"] == "SpaceX"
    assert payload["name"] == "SpaceX"
    assert api_context.client.get("/positions").json()[0]["symbol"] == "SpaceX"


def test_create_position_name_only_reuses_existing_name_or_pseudo_symbol(
    api_context: ApiTestContext,
) -> None:
    existing = api_context.client.post(
        "/positions",
        json={
            "symbol": "SpaceX",
            "market": "US",
            "kind": "watching",
        },
    )
    duplicate = api_context.client.post(
        "/positions",
        json={
            "market": "US",
            "name": "SpaceX",
            "kind": "watching",
        },
    )

    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == existing.json()["id"]
    assert len(api_context.client.get("/positions").json()) == 1


def test_list_positions_returns_local_user_positions(
    api_context: ApiTestContext,
) -> None:
    api_context.client.post(
        "/positions",
        json={
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple",
            "kind": "owned",
        },
    )
    api_context.client.post(
        "/positions",
        json={
            "symbol": "TSM",
            "market": "US",
            "name": "Taiwan Semiconductor",
            "kind": "watching",
        },
    )

    response = api_context.client.get("/positions")
    payload = response.json()
    by_symbol = {item["symbol"]: item for item in payload}

    assert response.status_code == 200
    assert set(by_symbol) == {"AAPL", "TSM"}
    assert by_symbol["AAPL"]["kind"] == "owned"
    assert by_symbol["TSM"]["kind"] == "watching"


def test_list_positions_returns_empty_list(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/positions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_positions_collapses_existing_duplicate_identity(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    started = api_context.client.post("/runs", json={"position_id": position_id})

    with connect(api_context.db_path) as conn:
        with with_tx(conn):
            conn.execute(
                """
                INSERT INTO positions(
                  id, user_id, symbol, market, name, kind, qty, cost_basis,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "position-duplicate-aapl",
                    "local-user",
                    "AAPL",
                    "US",
                    "Apple duplicate",
                    "owned",
                    None,
                    None,
                    "2026-06-26T00:00:01Z",
                    "2026-06-26T00:00:01Z",
                ),
            )

    response = api_context.client.get("/positions")
    payload = response.json()

    assert response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["id"] == position_id
    assert payload[0]["latest_run_id"] == started.json()["run_id"]


def test_list_positions_restores_latest_run_entity_from_checkpoint_snapshot(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    started = api_context.client.post("/runs", json={"position_id": position_id})
    run_id = started.json()["run_id"]

    with connect(api_context.db_path) as conn:
        with with_tx(conn):
            conn.execute("UPDATE run_registry SET entity_id = NULL WHERE id = ?", (run_id,))

    response = api_context.client.get("/positions")
    payload = response.json()

    assert response.status_code == 200
    assert payload[0]["latest_run_id"] == run_id
    assert payload[0]["latest_run_status"] == "awaiting_confirmation"
    assert payload[0]["latest_run_entity"] == {
        "id": "entity-aapl",
        "name": "Apple Inc.",
        "node_type": "company",
        "symbol": "AAPL",
        "market": "US",
    }


def _create_position(api_context: ApiTestContext) -> str:
    response = api_context.client.post(
        "/positions",
        json={
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple",
            "kind": "owned",
        },
    )
    return str(response.json()["id"])
