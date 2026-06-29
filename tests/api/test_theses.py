from time import sleep

from tests.api.conftest import ApiTestContext


def test_confirm_thesis_completes_run_across_requests(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    started = api_context.client.post("/runs", json={"position_id": position_id})
    run_id = str(started.json()["run_id"])
    detail_before = _wait_for_status(api_context, run_id, "awaiting_confirmation")
    thesis_id = str(detail_before["thesis_id"])

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


def _wait_for_status(
    api_context: ApiTestContext,
    run_id: str,
    expected_status: str,
) -> dict[str, object]:
    last_payload: dict[str, object] = {}
    for _ in range(40):
      response = api_context.client.get(f"/runs/{run_id}")
      last_payload = response.json()
      if last_payload.get("status") == expected_status:
          return last_payload
      sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach {expected_status}: {last_payload}")
