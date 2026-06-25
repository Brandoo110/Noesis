from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import EvidenceRow
from noesis.db.repos.evidences_repo import EvidencesRepo


NOW = "2026-06-26T00:00:00Z"


def make_evidence(id: str, run_id: str = "run-1") -> EvidenceRow:
    return EvidenceRow(
        id=id,
        run_id=run_id,
        entity_id="entity-1",
        source="web",
        source_tier=2,
        url="https://example.com",
        title="Evidence",
        snippet=f"Snippet {id}",
        captured_at=NOW,
        published_at=None,
        created_at=NOW,
    )


def test_evidences_repo_insert_many_get_and_list_by_run(db: Connection) -> None:
    repo = EvidencesRepo()
    first = make_evidence("evidence-1")
    second = make_evidence("evidence-2")

    with with_tx(db):
        repo.insert_many([first, second], conn=db)

    assert repo.get("evidence-1", conn=db) == first
    assert repo.list_by_run("run-1", conn=db) == [first, second]


def test_evidences_repo_empty_results(db: Connection) -> None:
    repo = EvidencesRepo()

    assert repo.get("missing", conn=db) is None
    assert repo.list_by_run("missing-run", conn=db) == []
