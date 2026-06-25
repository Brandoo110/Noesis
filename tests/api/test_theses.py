from tests.api.conftest import ApiTestContext


def test_confirm_thesis_completes_run_across_requests(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    started = api_context.client.post("/runs", json={"position_id": position_id})
    thesis_id = str(started.json()["thesis_id"])

    confirmed = api_context.client.post(
        f"/theses/{thesis_id}/confirm",
        json={"status": "confirmed"},
    )
    detail = api_context.client.get(f"/runs/{confirmed.json()['run_id']}")
    detail_payload = detail.json()

    assert api_context.checkpoint_path.exists()
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "completed"
    assert detail.status_code == 200
    assert detail_payload["thesis"]["status"] == "confirmed"
    assert detail_payload["thesis"]["assumptions"][0]["evidence_ids"]


def test_confirm_thesis_returns_error_for_unknown_run(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.post(
        "/theses/thesis-run-missing/confirm",
        json={"status": "confirmed"},
    )

    assert response.status_code == 502
    assert response.json()["reason"] == "run_not_found"


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
