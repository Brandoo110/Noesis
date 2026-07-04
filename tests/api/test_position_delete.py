import sqlite3

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate

from tests.api.conftest import ApiTestContext

TS = "2026-06-26T00:00:00Z"
POSITION_ID = "position-delete"
RUN_ID = "run-delete"


def test_delete_position_removes_run_artifacts_but_keeps_entities(api_context: ApiTestContext) -> None:
    _seed_position_with_run_artifacts(api_context)

    response = api_context.client.delete(f"/positions/{POSITION_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert api_context.client.get("/positions").json() == []
    with connect(api_context.db_path) as conn:
        assert _count(conn, "positions") == 0
        assert _count(conn, "entities") == 2
        for table in _run_artifact_tables():
            assert _count(conn, table) == 0
        expansion = conn.execute(
            "SELECT researched, researched_at, cached_run_id FROM node_expansions"
        ).fetchone()
        assert dict(expansion) == {
            "researched": 0,
            "researched_at": None,
            "cached_run_id": None,
        }


def test_delete_position_returns_404_for_missing_position(api_context: ApiTestContext) -> None:
    response = api_context.client.delete("/positions/position-missing")

    assert response.status_code == 404


def _seed_position_with_run_artifacts(api_context: ApiTestContext) -> None:
    with connect(api_context.db_path) as conn:
        migrate(conn)
        with with_tx(conn):
            _insert_position(conn)
            _insert_entities(conn)
            _insert_run(conn)
            _insert_trace(conn)
            _insert_evidence(conn)
            _insert_intel(conn)
            _insert_thesis(conn)
            _insert_graph_data(conn)
            _insert_agentops_data(conn)
            _insert_expansion(conn)


def _insert_position(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "positions",
        ("id", "user_id", "symbol", "market", "name", "kind", "qty", "cost_basis", "created_at", "updated_at"),
        (POSITION_ID, "local-user", "AAPL", "US", "Apple", "owned", None, None, TS, TS),
    )


def _insert_entities(conn: sqlite3.Connection) -> None:
    columns = (
        "id",
        "node_type",
        "name",
        "aliases_json",
        "identifiers_json",
        "market",
        "created_at",
        "updated_at",
    )
    _insert(conn, "entities", columns, ("entity-delete", "company", "Apple Inc.", "[]", '{"symbol":"AAPL"}', "US", TS, TS))
    _insert(conn, "entities", columns, ("entity-supplier", "company", "Supplier Inc.", "[]", '{"symbol":"SUP"}', "US", TS, TS))


def _insert_run(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "run_registry",
        ("id", "position_id", "entity_id", "node_kind", "status", "started_at", "ended_at", "created_at"),
        (RUN_ID, POSITION_ID, "entity-delete", "seed", "completed", TS, TS, TS),
    )


def _insert_trace(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "node_traces",
        (
            "id",
            "run_id",
            "node_name",
            "entity_id",
            "status",
            "evidence_ids_json",
            "started_at",
            "ended_at",
            "created_at",
        ),
        ("trace-delete", RUN_ID, "ingest", "entity-delete", "success", '["evidence-delete"]', TS, TS, TS),
    )


def _insert_evidence(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "evidences",
        ("id", "run_id", "entity_id", "source", "source_tier", "url", "title", "snippet", "captured_at", "created_at"),
        ("evidence-delete", RUN_ID, "entity-delete", "tavily", 2, "https://example.com/apple", "Apple supplier news", "Apple supplier update.", TS, TS),
    )
    conn.execute(
        "INSERT INTO evidences_fts(evidence_id, snippet, title) VALUES (?, ?, ?)",
        ("evidence-delete", "Apple supplier update.", "Apple supplier news"),
    )


def _insert_intel(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "intel_items",
        (
            "id",
            "entity_id",
            "run_id",
            "source",
            "source_tier",
            "title",
            "content",
            "sentiment_json",
            "event_type",
            "evidence_ids_json",
            "created_at",
        ),
        ("intel-delete", "entity-delete", RUN_ID, "tavily", 2, "Supplier update", "Apple supplier update.", '{"direction":"neutral","confidence":0.5}', "supply_chain", '["evidence-delete"]', TS),
    )


def _insert_thesis(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "theses",
        ("id", "position_id", "run_id", "summary", "status", "created_at", "updated_at"),
        ("thesis-delete", POSITION_ID, RUN_ID, "Apple has an evidence-backed research thesis.", "draft", TS, TS),
    )
    _insert(
        conn,
        "thesis_assumptions",
        ("id", "thesis_id", "text", "kind", "evidence_ids_json", "status", "created_at"),
        ("assumption-delete", "thesis-delete", "Supply evidence remains relevant.", "driver", '["evidence-delete"]', "draft", TS),
    )
    _insert(
        conn,
        "approvals",
        ("id", "run_id", "object_type", "object_id", "status", "payload_json", "created_at", "updated_at"),
        ("approval-delete", RUN_ID, "thesis", "thesis-delete", "confirmed", "{}", TS, TS),
    )


def _insert_graph_data(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "graph_edges",
        ("id", "from_entity_id", "to_entity_id", "relation", "basis", "confidence", "evidence_ids_json", "run_id", "rationale", "created_at"),
        ("edge-delete", "entity-delete", "entity-supplier", "supplier", "source_backed", 0.8, '["evidence-delete"]', RUN_ID, "Supplier evidence.", TS),
    )
    _insert(
        conn,
        "holding_relevances",
        ("id", "entity_id", "position_id", "path_json", "created_at"),
        ("relevance-delete", "entity-supplier", POSITION_ID, '["entity-supplier","entity-delete"]', TS),
    )


def _insert_agentops_data(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "source_documents",
        ("id", "run_id", "entity_id", "url", "title", "publisher", "fetched_at", "source_type", "reliability", "content_hash", "source_tier", "created_at"),
        ("source-delete", RUN_ID, "entity-delete", "https://example.com/apple", "Apple supplier news", "Example", TS, "news", 0.9, "hash-delete", 2, TS),
    )
    _insert(
        conn,
        "tool_invocations",
        (
            "id",
            "run_id",
            "trace_id",
            "tool_name",
            "status",
            "permission_level",
            "input_summary",
            "output_summary",
            "cache_hit",
            "retry_count",
            "latency_ms",
            "started_at",
            "created_at",
        ),
        ("tool-delete", RUN_ID, "trace-delete", "search.tavily", "success", "network", "query=AAPL", "1 result", 0, 0, 120, TS, TS),
    )


def _insert_expansion(conn: sqlite3.Connection) -> None:
    _insert(
        conn,
        "node_expansions",
        ("entity_id", "researched", "researched_at", "cached_run_id", "created_at", "updated_at"),
        ("entity-delete", 1, TS, RUN_ID, TS, TS),
    )


def _insert(
    conn: sqlite3.Connection,
    table: str,
    columns: tuple[str, ...],
    values: tuple[object, ...],
) -> None:
    placeholders = ", ".join("?" for _ in values)
    conn.execute(
        f"INSERT INTO {table}({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )


def _run_artifact_tables() -> tuple[str, ...]:
    return (
        "run_registry",
        "node_traces",
        "tool_invocations",
        "source_documents",
        "evidences",
        "evidences_fts",
        "intel_items",
        "theses",
        "thesis_assumptions",
        "approvals",
        "graph_edges",
        "holding_relevances",
    )


def _count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])
