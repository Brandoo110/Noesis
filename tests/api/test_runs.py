from noesis.db.connection import connect, with_tx
from noesis.db.models import RunRow
from noesis.db.repos.run_registry_repo import RunRegistryRepo

from tests.api.conftest import ApiTestContext
from tests.api.conftest import NOW


def test_start_run_and_get_detail_returns_grounded_draft(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)

    started = api_context.client.post("/runs", json={"position_id": position_id})
    run_payload = started.json()
    detail = api_context.client.get(f"/runs/{run_payload['run_id']}")
    detail_payload = detail.json()

    assert started.status_code == 200
    assert run_payload["status"] == "awaiting_confirmation"
    assert run_payload["thesis_id"] == f"thesis-{run_payload['run_id']}"
    assert detail.status_code == 200
    assert detail_payload["status"] == "awaiting_confirmation"
    assert detail_payload["entity"] == {
        "id": "entity-aapl",
        "name": "Apple Inc.",
        "node_type": "company",
        "symbol": "AAPL",
        "market": "US",
    }
    assert detail_payload["evidences"][0]["source_tier"] == 2
    assert detail_payload["intel_items"][0]["source_tier"] == 2
    assert detail_payload["intel_items"][0]["evidence_ids"]
    assert detail_payload["thesis"]["assumptions"][0]["evidence_ids"]


def test_get_running_run_detail_allows_null_entity(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    with connect(api_context.db_path) as conn:
        with with_tx(conn):
            RunRegistryRepo().insert(
                RunRow(
                    id="run-running",
                    position_id=position_id,
                    entity_id=None,
                    node_kind="seed",
                    status="running",
                    started_at=NOW,
                    ended_at=None,
                    created_at=NOW,
                ),
                conn=conn,
            )

    response = api_context.client.get("/runs/run-running")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "running"
    assert payload["entity"] is None


def test_start_run_returns_error_for_missing_position(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/runs",
        json={"position_id": "position-missing"},
    )

    assert response.status_code == 502
    assert response.json()["reason"] == "position_not_found"


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
