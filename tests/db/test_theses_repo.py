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


def test_theses_repo_latest_for_position_prefers_confirmed_then_latest(
    db: Connection,
) -> None:
    repo = ThesesRepo()
    with with_tx(db):
        repo.insert(make_thesis(), conn=db)
        repo.insert(
            ThesisRow(
                id="thesis-confirmed",
                position_id="position-1",
                run_id="run-confirmed",
                summary="Confirmed thesis",
                status="confirmed",
                created_at="2026-06-25T00:00:00Z",
                updated_at="2026-06-25T00:00:00Z",
            ),
            conn=db,
        )
        repo.insert(
            ThesisRow(
                id="thesis-newer-draft",
                position_id="position-1",
                run_id="run-newer",
                summary="Newer draft thesis",
                status="draft",
                created_at="2026-06-27T00:00:00Z",
                updated_at="2026-06-27T00:00:00Z",
            ),
            conn=db,
        )
        repo.insert(
            ThesisRow(
                id="thesis-other",
                position_id="position-2",
                run_id="run-other",
                summary="Other position thesis",
                status="draft",
                created_at="2026-06-28T00:00:00Z",
                updated_at="2026-06-28T00:00:00Z",
            ),
            conn=db,
        )

    row = repo.latest_for_position("position-1", conn=db)
    latest_other = repo.latest_for_position("position-2", conn=db)

    assert row is not None
    assert row.id == "thesis-confirmed"
    assert latest_other is not None
    assert latest_other.id == "thesis-other"
    assert repo.latest_for_position("missing", conn=db) is None
