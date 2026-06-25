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
