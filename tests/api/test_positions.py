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
