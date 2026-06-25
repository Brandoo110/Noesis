from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import RunRow
from noesis.db.repos.run_registry_repo import RunRegistryRepo


NOW = "2026-06-26T00:00:00Z"


def make_run() -> RunRow:
    return RunRow(
        id="run-1",
        position_id="position-1",
        entity_id="entity-1",
        node_kind="seed",
        status="running",
        started_at=NOW,
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
