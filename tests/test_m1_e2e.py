from sqlite3 import Connection
from time import sleep

import pytest

from noesis.db.connection import connect
from noesis.db.models import IntelItemRow
from noesis.db.repos.evidences_repo import EvidencesRepo
from noesis.db.repos.intel_items_repo import IntelItemsRepo
from noesis.db.repos.node_traces_repo import NodeTracesRepo
from noesis.db.repos.theses_repo import ThesesRepo
from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo
from noesis.graph.build_graph import SEED_NODE_ORDER
from tests.api.conftest import ApiTestContext

pytest_plugins = ("tests.api.conftest",)


def test_m1_api_happy_path_persists_grounded_outputs(
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

    conn = connect(api_context.db_path)
    try:
        evidence_ids = _assert_persisted_outputs(conn, run_id, thesis_id)
        traces = NodeTracesRepo().list_by_run(run_id, conn=conn)
    finally:
        conn.close()

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "completed"
    assert set(SEED_NODE_ORDER).issubset({trace.node_name for trace in traces})
    assert evidence_ids


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


def _assert_persisted_outputs(
    conn: Connection, run_id: str, thesis_id: str
) -> set[str]:
    thesis = ThesesRepo().get(thesis_id, conn=conn)
    assumptions = ThesisAssumptionsRepo().list_by_thesis(thesis_id, conn=conn)
    evidences = EvidencesRepo().list_by_run(run_id, conn=conn)
    evidence_ids = {item.id for item in evidences}
    assert thesis is not None
    assert assumptions
    assert evidences
    intel_rows = _intel_rows(conn, run_id)
    assert intel_rows
    for row in intel_rows:
        assert set(row.evidence_ids()).issubset(evidence_ids)
    for row in assumptions:
        assert row.evidence_ids()
        assert set(row.evidence_ids()).issubset(evidence_ids)
    return evidence_ids


def _intel_rows(conn: Connection, run_id: str) -> list[IntelItemRow]:
    row = conn.execute(
        "SELECT entity_id FROM intel_items WHERE run_id = ? LIMIT 1",
        (run_id,),
    ).fetchone()
    if row is None:
        return []
    return IntelItemsRepo().list_by_entity(row["entity_id"], conn=conn)


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
