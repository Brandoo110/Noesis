from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EvidenceRow
from noesis.db.repos.evidences_repo import EvidencesRepo
from tests.api.conftest import ApiTestContext, NOW


def test_get_evidence_returns_explicit_response(api_context: ApiTestContext) -> None:
    _seed_evidence(api_context)

    response = api_context.client.get("/evidences/evidence-1")
    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "id": "evidence-1",
        "source": "web",
        "source_tier": 2,
        "url": "https://example.com/evidence-1",
        "title": "Evidence",
        "snippet": "Evidence snippet",
        "captured_at": NOW,
        "published_at": None,
    }


def test_get_evidence_returns_404_for_missing_id(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/evidences/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "evidence not found"


def _seed_evidence(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            EvidencesRepo().insert_many(
                [
                    EvidenceRow(
                        id="evidence-1",
                        run_id="run-1",
                        entity_id="entity-aapl",
                        source="web",
                        source_tier=2,
                        url="https://example.com/evidence-1",
                        title="Evidence",
                        snippet="Evidence snippet",
                        captured_at=NOW,
                        published_at=None,
                        created_at=NOW,
                    )
                ],
                conn=conn,
            )
    finally:
        conn.close()
