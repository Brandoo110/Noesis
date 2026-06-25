from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import IntelItemRow
from noesis.db.repos.intel_items_repo import IntelItemsRepo


NOW = "2026-06-26T00:00:00Z"


def make_intel(id: str, entity_id: str = "entity-1") -> IntelItemRow:
    return IntelItemRow(
        id=id,
        entity_id=entity_id,
        run_id="run-1",
        source="web",
        source_tier=2,
        title="Intel",
        content=f"Intel {id}",
        url="https://example.com",
        published_at=None,
        sentiment_json='{"dir": "neutral", "conf": 0.7}',
        event_type="news",
        evidence_ids_json='["evidence-1"]',
        created_at=NOW,
    )


def test_intel_items_repo_insert_many_and_list_by_entity(db: Connection) -> None:
    repo = IntelItemsRepo()
    first = make_intel("intel-1")
    second = make_intel("intel-2")

    with with_tx(db):
        repo.insert_many([first, second], conn=db)

    assert repo.list_by_entity("entity-1", conn=db) == [first, second]


def test_intel_items_repo_empty_result(db: Connection) -> None:
    assert IntelItemsRepo().list_by_entity("missing", conn=db) == []
