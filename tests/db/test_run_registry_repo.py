from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import RunRow
from noesis.db.repos.run_registry_repo import RunRegistryRepo


NOW = "2026-06-26T00:00:00Z"


def make_run(
    id: str = "run-1",
    position_id: str = "position-1",
    *,
    status: str = "running",
    started_at: str = NOW,
) -> RunRow:
    return RunRow(
        id=id,
        position_id=position_id,
        entity_id="entity-1",
        node_kind="seed",
        status=status,
        started_at=started_at,
        ended_at=None,
        created_at=NOW,
    )


def test_run_registry_repo_insert_get_and_set_status(db: Connection) -> None:
    repo = RunRegistryRepo()

    with with_tx(db):
        repo.insert(make_run(), conn=db)
        repo.set_status("run-1", "completed", NOW, conn=db)

    row = repo.get("run-1", conn=db)

    assert row is not None
    assert row.status == "completed"
    assert row.ended_at == NOW


def test_run_registry_repo_empty_result(db: Connection) -> None:
    repo = RunRegistryRepo()

    assert repo.get("missing", conn=db) is None


def test_run_registry_repo_lists_latest_seed_for_positions(
    db: Connection,
) -> None:
    repo = RunRegistryRepo()

    with with_tx(db):
        repo.insert(make_run("run-old", "position-1"), conn=db)
        repo.insert(
            make_run(
                "run-new",
                "position-1",
                status="completed",
                started_at="2026-06-27T00:00:00Z",
            ),
            conn=db,
        )
        repo.insert(make_run("run-other", "position-2", status="failed"), conn=db)

    rows = repo.latest_seed_for_positions(["position-1", "position-2"], conn=db)

    assert [row.id for row in rows] == ["run-new", "run-other"]
    assert repo.latest_seed_for_positions([], conn=db) == []
