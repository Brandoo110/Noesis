from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import PositionRow
from noesis.db.repos.positions_repo import PositionsRepo


NOW = "2026-06-26T00:00:00Z"


def make_position(id: str, user_id: str = "user-1") -> PositionRow:
    return PositionRow(
        id=id,
        user_id=user_id,
        symbol="AAPL",
        market="US",
        name="Apple",
        kind="owned",
        qty=None,
        cost_basis=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_positions_repo_insert_get_and_list_by_user(db: Connection) -> None:
    repo = PositionsRepo()
    row = make_position("position-1")

    with with_tx(db):
        repo.insert(row, conn=db)

    assert repo.get("position-1", conn=db) == row
    assert repo.list_by_user("user-1", conn=db) == [row]


def test_positions_repo_lists_matching_identity_case_insensitively(
    db: Connection,
) -> None:
    repo = PositionsRepo()
    row = make_position("position-1")

    with with_tx(db):
        repo.insert(row, conn=db)

    assert repo.list_by_identity(
        "user-1",
        "aapl",
        "us",
        "owned",
        conn=db,
    ) == [row]
    assert repo.list_by_identity(
        "user-1",
        "aapl",
        "us",
        "watching",
        conn=db,
    ) == []


def test_positions_repo_empty_results(db: Connection) -> None:
    repo = PositionsRepo()

    assert repo.get("missing", conn=db) is None
    assert repo.list_by_user("missing-user", conn=db) == []
