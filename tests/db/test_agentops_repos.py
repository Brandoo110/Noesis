from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import (
    SourceDocumentRow,
    ToolCacheEntryRow,
    ToolInvocationRow,
)
from noesis.db.repos.source_documents_repo import SourceDocumentsRepo
from noesis.db.repos.tool_cache_entries_repo import ToolCacheEntriesRepo
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo

NOW = "2026-06-26T00:00:00Z"


def make_source_document(id: str = "source-doc-1") -> SourceDocumentRow:
    return SourceDocumentRow(
        id=id,
        run_id="run-1",
        entity_id="entity-aapl",
        url="https://example.com/apple",
        title="Apple supplier update",
        publisher="Example News",
        published_at=None,
        fetched_at=NOW,
        source_type="news",
        reliability=0.8,
        content_hash="hash-1",
        source_tier=2,
        created_at=NOW,
    )


def make_tool_invocation(
    id: str = "tool-call-1",
    *,
    run_id: str = "run-1",
    status: str = "success",
    cache_hit: bool = False,
) -> ToolInvocationRow:
    return ToolInvocationRow(
        id=id,
        run_id=run_id,
        trace_id="trace-1",
        tool_name="search.web",
        status=status,
        permission_level="network",
        input_summary="query=AAPL supplier",
        output_summary="8 docs" if status == "success" else None,
        error_message=None if status == "success" else "timeout",
        cache_key="search:AAPL",
        cache_hit=cache_hit,
        retry_count=1,
        latency_ms=240,
        token_input=100,
        token_output=40,
        estimated_cost_usd=0.0012,
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )


def make_cache_entry(hit_count: int = 0) -> ToolCacheEntryRow:
    return ToolCacheEntryRow(
        id="cache-1",
        cache_key="search:AAPL",
        tool_name="search.web",
        cache_policy="ttl",
        ttl_seconds=86400,
        expires_at="2026-06-27T00:00:00Z",
        hit_count=hit_count,
        last_hit_at=NOW if hit_count else None,
        payload_hash="payload-hash",
        payload_json='{"ok": true}',
        created_at=NOW,
        updated_at=NOW,
    )


def test_source_documents_repo_insert_list_and_get_by_hash(
    db: Connection,
) -> None:
    repo = SourceDocumentsRepo()
    row = make_source_document()

    with with_tx(db):
        repo.insert_many([row], conn=db)

    assert repo.list_by_run("run-1", conn=db) == [row]
    assert repo.get_by_content_hash("hash-1", conn=db) == row
    assert repo.list_by_run("missing", conn=db) == []


def test_tool_invocations_repo_insert_and_list_by_run(
    db: Connection,
) -> None:
    repo = ToolInvocationsRepo()
    first = make_tool_invocation("tool-call-1", run_id="run-1", cache_hit=True)
    second = make_tool_invocation("tool-call-2", run_id="run-2", status="failed")

    with with_tx(db):
        repo.insert(first, conn=db)
        repo.insert(second, conn=db)

    assert repo.list_by_run("run-1", conn=db) == [first]
    assert repo.list_by_run_ids(["run-1", "run-2"], conn=db) == [first, second]
    assert repo.list_by_run_ids([], conn=db) == []


def test_tool_cache_entries_repo_upsert_get_and_record_hit(
    db: Connection,
) -> None:
    repo = ToolCacheEntriesRepo()

    assert repo.get_by_key("search:AAPL", conn=db) is None

    with with_tx(db):
        repo.upsert(make_cache_entry(), conn=db)

    assert repo.get_by_key("search:AAPL", conn=db) == make_cache_entry()

    with with_tx(db):
        repo.record_hit("search:AAPL", NOW, conn=db)

    row = repo.get_by_key("search:AAPL", conn=db)
    assert row is not None
    assert row.hit_count == 1
    assert row.last_hit_at == NOW
