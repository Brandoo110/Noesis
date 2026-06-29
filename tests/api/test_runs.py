import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import (
    EntityRow,
    EvidenceRow,
    IntelItemRow,
    PositionRow,
    RunRow,
    ThesisAssumptionRow,
    ThesisRow,
)
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.evidences_repo import EvidencesRepo
from noesis.db.repos.intel_items_repo import IntelItemsRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.theses_repo import ThesesRepo
from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo

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
    assert run_payload["status"] == "running"
    assert run_payload["thesis_id"] is None
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


def test_start_run_reuses_running_seed_for_same_position(
    api_context: ApiTestContext,
) -> None:
    position_id = _create_position(api_context)
    with connect(api_context.db_path) as conn:
        with with_tx(conn):
            RunRegistryRepo().insert(
                RunRow(
                    id="run-existing",
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

    response = api_context.client.post("/runs", json={"position_id": position_id})
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_id"] == "run-existing"
    assert payload["status"] == "running"
    with connect(api_context.db_path) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) FROM run_registry
            WHERE position_id = ? AND node_kind = 'seed'
            """,
            (position_id,),
        ).fetchone()[0]
    assert count == 1


def test_get_run_detail_falls_back_to_persisted_db_outputs(
    api_context: ApiTestContext,
) -> None:
    _seed_persisted_run(api_context)

    response = api_context.client.get("/runs/run-db")
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_id"] == "run-db"
    assert payload["status"] == "completed"
    assert payload["evidences"] == [
        {
            "id": "evidence-db",
            "source": "web",
            "source_tier": 2,
            "url": "https://example.com/db-evidence",
            "title": "Persisted evidence",
            "snippet": "Persisted Apple evidence.",
            "captured_at": NOW,
            "published_at": None,
        }
    ]
    assert payload["intel_items"] == [
        {
            "title": "Persisted supplier update",
            "content": "Persisted evidence-backed content.",
            "event_type": "supply_chain",
            "source": "web",
            "source_tier": 2,
            "url": "https://example.com/db-evidence",
            "published_at": None,
            "sentiment": {"dir": "neutral", "conf": 0.7},
            "evidence_ids": ["evidence-db"],
        }
    ]
    assert payload["thesis"] == {
        "id": "thesis-run-db",
        "summary": "Persisted thesis summary.",
        "status": "confirmed",
        "assumptions": [
            {
                "text": "Persisted assumption with evidence.",
                "kind": "assumption",
                "evidence_ids": ["evidence-db"],
            }
        ],
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


def _seed_persisted_run(api_context: ApiTestContext) -> None:
    with connect(api_context.db_path) as conn:
        migrate(conn)
        with with_tx(conn):
            PositionsRepo().insert(
                PositionRow(
                    id="position-db",
                    user_id="local-user",
                    symbol="AAPL",
                    market="US",
                    name="Apple",
                    kind="owned",
                    qty=None,
                    cost_basis=None,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
            EntitiesRepo().upsert(
                EntityRow(
                    id="entity-db",
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
            RunRegistryRepo().insert(
                RunRow(
                    id="run-db",
                    position_id="position-db",
                    entity_id="entity-db",
                    node_kind="seed",
                    status="completed",
                    started_at=NOW,
                    ended_at=NOW,
                    created_at=NOW,
                ),
                conn=conn,
            )
            EvidencesRepo().insert_many(
                [
                    EvidenceRow(
                        id="evidence-db",
                        run_id="run-db",
                        entity_id="entity-db",
                        source="web",
                        source_tier=2,
                        url="https://example.com/db-evidence",
                        title="Persisted evidence",
                        snippet="Persisted Apple evidence.",
                        captured_at=NOW,
                        published_at=None,
                        created_at=NOW,
                    )
                ],
                conn=conn,
            )
            IntelItemsRepo().insert_many(
                [
                    IntelItemRow(
                        id="intel-db",
                        entity_id="entity-db",
                        run_id="run-db",
                        source="web",
                        source_tier=2,
                        title="Persisted supplier update",
                        content="Persisted evidence-backed content.",
                        url="https://example.com/db-evidence",
                        published_at=None,
                        sentiment_json=json.dumps({"dir": "neutral", "conf": 0.7}),
                        event_type="supply_chain",
                        evidence_ids_json=json.dumps(["evidence-db"]),
                        created_at=NOW,
                    )
                ],
                conn=conn,
            )
            ThesesRepo().insert(
                ThesisRow(
                    id="thesis-run-db",
                    position_id="position-db",
                    run_id="run-db",
                    summary="Persisted thesis summary.",
                    status="confirmed",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
            ThesisAssumptionsRepo().insert_many(
                [
                    ThesisAssumptionRow(
                        id="assumption-db",
                        thesis_id="thesis-run-db",
                        text="Persisted assumption with evidence.",
                        kind="assumption",
                        evidence_ids_json=json.dumps(["evidence-db"]),
                        status="active",
                        created_at=NOW,
                    )
                ],
                conn=conn,
            )
