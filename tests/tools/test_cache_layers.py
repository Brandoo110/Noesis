import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo
from noesis.tools.cache_layers import ToolCacheLayers
from noesis.tools.registry import ToolExecutor, default_tool_registry

NOW = "2026-06-26T00:00:00Z"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_webpage_pdf_and_embedding_caches_log_hit_miss(
    db: sqlite3.Connection,
) -> None:
    executor = ToolExecutor(conn=db, registry=default_tool_registry(), now=lambda: NOW)
    cache = ToolCacheLayers(executor)
    calls = {"web": 0, "pdf": 0, "embedding": 0}

    def fetch_web() -> str:
        calls["web"] += 1
        return "html body"

    def parse_pdf() -> str:
        calls["pdf"] += 1
        return "pdf text"

    def embed() -> list[float]:
        calls["embedding"] += 1
        return [0.1, 0.2]

    assert cache.webpage_content("run-1", "https://example.com/a", fetch_web) == "html body"
    assert cache.webpage_content("run-1", "https://example.com/a", fetch_web) == "html body"
    assert cache.pdf_parse("run-1", "https://example.com/a.pdf", parse_pdf) == "pdf text"
    assert cache.pdf_parse("run-1", "https://example.com/a.pdf", parse_pdf) == "pdf text"
    assert cache.embedding_vector("run-1", "hello world", embed) == [0.1, 0.2]
    assert cache.embedding_vector("run-1", "hello world", embed) == [0.1, 0.2]

    assert calls == {"web": 1, "pdf": 1, "embedding": 1}
    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert [row.tool_name for row in invocations] == [
        "webpage.fetch",
        "webpage.fetch",
        "pdf.parse",
        "pdf.parse",
        "embedding.vector",
        "embedding.vector",
    ]
    assert [row.cache_hit for row in invocations] == [
        False,
        True,
        False,
        True,
        False,
        True,
    ]
