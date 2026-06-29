from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import ThesisRow
from noesis.db.repos.theses_repo import ThesesRepo


NOW = "2026-06-26T00:00:00Z"


def make_thesis(
    id: str = "thesis-1",
    run_id: str = "run-1",
    *,
    position_id: str = "position-1",
) -> ThesisRow:
    return ThesisRow(
        id=id,
        position_id=position_id,
        run_id=run_id,
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


def test_theses_repo_lists_by_run_ids(db: Connection) -> None:
    repo = ThesesRepo()
    first = make_thesis("thesis-1", "run-1")
    second = make_thesis("thesis-2", "run-2", position_id="position-2")
    skipped = make_thesis("thesis-3", "run-3", position_id="position-3")

    with with_tx(db):
        repo.insert(first, conn=db)
        repo.insert(second, conn=db)
        repo.insert(skipped, conn=db)

    rows = repo.list_by_run_ids(["run-1", "run-2"], conn=db)

    assert {row.id for row in rows} == {"thesis-1", "thesis-2"}
    assert repo.list_by_run_ids([], conn=db) == []


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
