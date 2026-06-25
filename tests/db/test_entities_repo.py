from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import EntityRow
from noesis.db.repos.entities_repo import EntitiesRepo


NOW = "2026-06-26T00:00:00Z"


def make_entity(id: str, name: str = "Apple") -> EntityRow:
    return EntityRow(
        id=id,
        node_type="company",
        name=name,
        aliases_json='["AAPL"]',
        identifiers_json='{"symbol": "AAPL"}',
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def test_entities_repo_upsert_get_and_find_by_symbol(db: Connection) -> None:
    repo = EntitiesRepo()
    row = make_entity("entity-1")

    with with_tx(db):
        first = repo.upsert(row, conn=db)
        second = repo.upsert(make_entity("entity-2"), conn=db)

    assert first == row
    assert second == row
    assert repo.get("entity-1", conn=db) == row
    assert repo.find_by_symbol("US", "AAPL", conn=db) == row


def test_entities_repo_empty_results(db: Connection) -> None:
    repo = EntitiesRepo()

    assert repo.get("missing", conn=db) is None
    assert repo.find_by_symbol("US", "MSFT", conn=db) is None
