import pytest

from tests.api.conftest import ApiTestContext


def test_resolve_position_returns_resolved_entity(api_context: ApiTestContext) -> None:
    response = api_context.client.post(
        "/positions/resolve",
        json={"name": "apple computer", "market": "us", "kind": "owned"},
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "resolved"
    assert payload["name"] == "Apple Inc."
    assert payload["symbol"] == "AAPL"
    assert payload["market"] == "US"
    assert payload["existing_position_id"] is None
    assert payload["existing_position_label"] is None


def test_resolve_position_flags_existing_position(api_context: ApiTestContext) -> None:
    created = api_context.client.post(
        "/positions",
        json={"symbol": "AAPL", "market": "US", "name": "Apple", "kind": "owned"},
    )

    response = api_context.client.post(
        "/positions/resolve",
        json={"name": "apple", "market": "US", "kind": "owned"},
    )

    payload = response.json()

    assert payload["status"] == "resolved"
    assert payload["existing_position_id"] == created.json()["id"]
    assert payload["existing_position_label"] == "AAPL"


def test_resolve_position_rejects_missing_symbol_and_name(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post("/positions/resolve", json={"market": "US"})

    assert response.status_code == 422


def test_resolve_position_returns_unresolved_when_llm_cannot_resolve(
    api_context: ApiTestContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "noesis.api.routes.positions.preview_resolve",
        lambda raw_input, deps: None,
    )

    response = api_context.client.post(
        "/positions/resolve",
        json={"name": "unknown corp", "market": "US", "kind": "owned"},
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "unresolved"
    assert payload["symbol"] is None
    assert payload["name"] == "unknown corp"
