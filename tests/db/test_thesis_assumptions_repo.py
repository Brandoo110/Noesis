from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import ThesisAssumptionRow
from noesis.db.repos.thesis_assumptions_repo import ThesisAssumptionsRepo


NOW = "2026-06-26T00:00:00Z"


def make_assumption(id: str, thesis_id: str = "thesis-1") -> ThesisAssumptionRow:
    return ThesisAssumptionRow(
        id=id,
        thesis_id=thesis_id,
        text="Evidence-backed risk",
        kind="risk",
        evidence_ids_json='["evidence-1"]',
        status="draft",
        created_at=NOW,
    )


def test_thesis_assumptions_repo_insert_many_and_list_by_thesis(
    db: Connection,
) -> None:
    repo = ThesisAssumptionsRepo()
    first = make_assumption("assumption-1")
    second = make_assumption("assumption-2")

    with with_tx(db):
        repo.insert_many([first, second], conn=db)

    assert repo.list_by_thesis("thesis-1", conn=db) == [first, second]


def test_thesis_assumptions_repo_empty_result(db: Connection) -> None:
    assert ThesisAssumptionsRepo().list_by_thesis("missing", conn=db) == []
