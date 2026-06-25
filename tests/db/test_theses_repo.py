from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import ThesisRow
from noesis.db.repos.theses_repo import ThesesRepo


NOW = "2026-06-26T00:00:00Z"


def make_thesis() -> ThesisRow:
    return ThesisRow(
        id="thesis-1",
        position_id="position-1",
        run_id="run-1",
        summary="Draft thesis",
        status="draft",
        created_at=NOW,
        updated_at=NOW,
    )


def test_theses_repo_insert_get_and_set_status(db: Connection) -> None:
    repo = ThesesRepo()

    with with_tx(db):
        repo.insert(make_thesis(), conn=db)
        repo.set_status("thesis-1", "confirmed", NOW, conn=db)

    row = repo.get("thesis-1", conn=db)

    assert row is not None
    assert row.status == "confirmed"
    assert row.updated_at == NOW


def test_theses_repo_empty_result(db: Connection) -> None:
    assert ThesesRepo().get("missing", conn=db) is None
