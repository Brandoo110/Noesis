import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.db.repos.tool_cache_entries_repo import ToolCacheEntriesRepo
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo
from noesis.graph.schemas import IngestedDoc
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.providers import LLMCompletion, LLMUsage
from noesis.tools.llm.router import LLMRole
from noesis.tools.registry import (
    CachePolicy,
    RetryPolicy,
    ToolAwareLLMRouter,
    ToolAwareSearchAdapter,
    ToolCallRequest,
    ToolDescriptor,
    ToolExecutionError,
    ToolExecutor,
    ToolRegistry,
    default_tool_registry,
)

NOW = "2026-06-26T00:00:00Z"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_default_tool_registry_exposes_search_llm_and_retrieval_metadata() -> None:
    registry = default_tool_registry()

    search = registry.get("search.tavily")
    llm = registry.get("llm.light")
    retrieval = registry.get("retrieval.evidence")

    assert search.permission_level == "network"
    assert search.timeout_seconds == 20
    assert search.retry_policy.max_attempts == 2
    assert search.cache_policy.mode == "ttl"
    assert llm.permission_level == "model"
    assert llm.cache_policy.mode == "none"
    assert retrieval.permission_level == "local"


def test_tool_executor_persists_success_and_returns_cached_result(
    db: sqlite3.Connection,
) -> None:
    executor = ToolExecutor(conn=db, registry=default_tool_registry(), now=lambda: NOW)
    calls = {"count": 0}

    def action() -> list[str]:
        calls["count"] += 1
        return ["doc-1"]

    request = ToolCallRequest(
        run_id="run-1",
        input_summary="query=AAPL",
        cache_key="search:AAPL",
    )

    first = executor.execute(
        "search.tavily",
        request,
        action,
        serialize_result=json.dumps,
        deserialize_result=lambda raw: list(json.loads(raw)),
        summarize_result=lambda result: f"{len(result)} docs",
    )
    second = executor.execute(
        "search.tavily",
        request,
        action,
        serialize_result=json.dumps,
        deserialize_result=lambda raw: list(json.loads(raw)),
        summarize_result=lambda result: f"{len(result)} docs",
    )

    assert first == ["doc-1"]
    assert second == ["doc-1"]
    assert calls["count"] == 1

    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert [row.cache_hit for row in invocations] == [False, True]
    assert [row.status for row in invocations] == ["success", "success"]

    cache = ToolCacheEntriesRepo().get_by_key("search:AAPL", conn=db)
    assert cache is not None
    assert cache.hit_count == 1
    assert cache.payload_json == '["doc-1"]'


def test_tool_executor_retries_and_logs_failure(
    db: sqlite3.Connection,
) -> None:
    registry = ToolRegistry(
        [
            ToolDescriptor(
                name="unstable.tool",
                description="unstable test tool",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                permission_level="local",
                timeout_seconds=1,
                retry_policy=RetryPolicy(max_attempts=2),
                cache_policy=CachePolicy(mode="none"),
            )
        ]
    )
    executor = ToolExecutor(conn=db, registry=registry, now=lambda: NOW)

    with pytest.raises(ToolExecutionError):
        executor.execute(
            "unstable.tool",
            ToolCallRequest(run_id="run-1", input_summary="boom"),
            lambda: (_ for _ in ()).throw(ValueError("boom")),
        )

    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert len(invocations) == 1
    assert invocations[0].status == "failed"
    assert invocations[0].retry_count == 1
    assert invocations[0].error_message == "boom"


def test_tool_aware_search_adapter_uses_registry_cache(
    db: sqlite3.Connection,
) -> None:
    adapter = CountingSearchAdapter()
    executor = ToolExecutor(conn=db, registry=default_tool_registry(), now=lambda: NOW)
    wrapped = ToolAwareSearchAdapter(adapter, executor)

    first = wrapped.search("AAPL suppliers", run_id="run-1", limit=2)
    second = wrapped.search("AAPL suppliers", run_id="run-1", limit=2)

    assert [item.title for item in first] == ["Apple"]
    assert [item.title for item in second] == ["Apple"]
    assert adapter.calls == 1
    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert [row.tool_name for row in invocations] == ["search.tavily", "search.tavily"]
    assert [row.cache_hit for row in invocations] == [False, True]


def test_tool_aware_llm_router_logs_text_calls(db: sqlite3.Connection) -> None:
    executor = ToolExecutor(conn=db, registry=default_tool_registry(), now=lambda: NOW)
    router = ToolAwareLLMRouter(
        FakeLLMRouter(text_by_role={LLMRole.LIGHT: "ok"}),
        executor,
    )

    assert router.available(LLMRole.LIGHT)
    assert router.complete_text(LLMRole.LIGHT, "hello", run_id="run-1") == "ok"

    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert len(invocations) == 1
    assert invocations[0].tool_name == "llm.light"
    assert invocations[0].permission_level == "model"
    assert invocations[0].cache_hit is False


def test_tool_aware_llm_router_logs_provider_usage(db: sqlite3.Connection) -> None:
    executor = ToolExecutor(conn=db, registry=default_tool_registry(), now=lambda: NOW)
    router = ToolAwareLLMRouter(UsageLLMRouter(), executor)

    assert router.complete_text(LLMRole.SYNTH, "hello", run_id="run-1") == "ok"

    invocations = ToolInvocationsRepo().list_by_run("run-1", conn=db)
    assert len(invocations) == 1
    assert invocations[0].tool_name == "llm.synth"
    assert invocations[0].token_input == 11
    assert invocations[0].token_output == 7
    assert invocations[0].estimated_cost_usd == 0.003


class CountingSearchAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        self.calls += 1
        return [
            IngestedDoc(
                source="fixture",
                source_tier=2,
                title="Apple",
                url="https://example.com/apple",
                text=f"{query}:{limit}",
                published_at=None,
            )
        ]


class UsageLLMRouter:
    def available(self, role: LLMRole) -> bool:
        return True

    def complete_text_with_usage(
        self, role: LLMRole, prompt: str
    ) -> LLMCompletion:
        return LLMCompletion(
            text="ok",
            usage=LLMUsage(
                token_input=11,
                token_output=7,
                estimated_cost_usd=0.003,
            ),
        )
