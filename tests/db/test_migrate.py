from pathlib import Path
from sqlite3 import Connection

import pytest

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate


DOMAIN_TABLES = {
    "positions",
    "entities",
    "run_registry",
    "node_traces",
    "evidences",
    "intel_items",
    "theses",
    "thesis_assumptions",
    "approvals",
    "graph_edges",
    "node_expansions",
    "holding_relevances",
}


def table_names(conn: Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
    ).fetchall()
    return {row["name"] for row in rows}


def index_names(conn: Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {row["name"] for row in rows}


def test_migrate_creates_domain_tables_and_fts(db: Connection) -> None:
    names = table_names(db)

    assert DOMAIN_TABLES.issubset(names)
    assert "evidences_fts" in names


def test_migrate_creates_required_indexes(db: Connection) -> None:
    names = index_names(db)

    assert {
        "idx_entities_symbol",
        "idx_runs_position",
        "idx_traces_run",
        "idx_evidences_run",
        "idx_intel_entity",
        "idx_theses_position",
        "idx_assumptions_thesis",
        "idx_approvals_run",
        "idx_edges_from",
        "idx_edges_to",
        "idx_node_expansions_researched",
        "idx_relevance_entity",
    }.issubset(names)


def test_migrate_is_idempotent(db: Connection) -> None:
    before = table_names(db)

    migrate(db)

    assert table_names(db) == before


def test_connect_configures_row_factory_foreign_keys_and_wal(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT 1 AS value").fetchone()
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()["foreign_keys"]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"]
    finally:
        conn.close()

    assert row["value"] == 1
    assert foreign_keys == 1
    assert journal_mode.lower() == "wal"


def test_with_tx_commits_and_rolls_back(db: Connection) -> None:
    with with_tx(db):
        db.execute(
            """
            INSERT INTO positions(
              id, user_id, symbol, market, name, kind, qty, cost_basis,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "position-1",
                "user-1",
                "AAPL",
                "US",
                "Apple",
                "owned",
                None,
                None,
                "2026-06-26T00:00:00Z",
                "2026-06-26T00:00:00Z",
            ),
        )

    assert db.execute("SELECT COUNT(*) AS qty FROM positions").fetchone()["qty"] == 1

    with pytest.raises(RuntimeError):
        with with_tx(db):
            db.execute(
                """
                INSERT INTO positions(
                  id, user_id, symbol, market, name, kind, qty, cost_basis,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "position-2",
                    "user-1",
                    "MSFT",
                    "US",
                    "Microsoft",
                    "watching",
                    None,
                    None,
                    "2026-06-26T00:00:00Z",
                    "2026-06-26T00:00:00Z",
                ),
            )
            raise RuntimeError("force rollback")

    assert db.execute("SELECT COUNT(*) AS qty FROM positions").fetchone()["qty"] == 1
