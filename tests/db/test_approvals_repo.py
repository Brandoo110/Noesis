from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import ApprovalRow
from noesis.db.repos.approvals_repo import ApprovalsRepo


NOW = "2026-06-26T00:00:00Z"


def make_approval() -> ApprovalRow:
    return ApprovalRow(
        id="approval-1",
        run_id="run-1",
        object_type="thesis",
        object_id="thesis-1",
        status="pending",
        payload_json='{"summary": "Draft"}',
        created_at=NOW,
        updated_at=NOW,
    )


def test_approvals_repo_insert_get_by_object_and_set_status(
    db: Connection,
) -> None:
    repo = ApprovalsRepo()

    with with_tx(db):
        repo.insert(make_approval(), conn=db)
        repo.set_status("approval-1", "confirmed", NOW, conn=db)

    row = repo.get_by_object("thesis", "thesis-1", conn=db)

    assert row is not None
    assert row.status == "confirmed"
    assert row.updated_at == NOW


def test_approvals_repo_empty_result(db: Connection) -> None:
    assert ApprovalsRepo().get_by_object("thesis", "missing", conn=db) is None
