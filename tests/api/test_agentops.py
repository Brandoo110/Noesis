import sqlite3
from pathlib import Path

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import (
    EvidenceRow,
    NodeTraceRow,
    RunRow,
    ToolInvocationRow,
)
from noesis.db.repos.evidences_repo import EvidencesRepo
from noesis.db.repos.node_traces_repo import NodeTracesRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo

from tests.api.conftest import ApiTestContext
from tests.api.conftest import NOW

END = "2026-06-26T00:00:03Z"


def test_get_runs_lists_agentops_summary(api_context: ApiTestContext) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.get("/runs")
    payload = response.json()

    assert response.status_code == 200
    assert payload["runs"] == [
        {
            "run_id": "run-agentops",
            "status": "completed",
            "started_at": NOW,
            "ended_at": END,
            "latency_ms": 3000,
            "evidence_count": 1,
            "tool_count": 2,
            "cache_hit_rate": 0.5,
        }
    ]


def test_get_run_trace_combines_node_and_tool_timeline(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.get("/runs/run-agentops/trace")
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_id"] == "run-agentops"
    assert payload["status"] == "completed"
    assert [step["kind"] for step in payload["steps"]] == ["node", "tool", "tool"]
    assert payload["steps"][0]["name"] == "ingest"
    assert payload["steps"][0]["evidence_ids"] == ["evidence-agentops"]
    assert payload["steps"][1]["name"] == "search.tavily"
    assert payload["steps"][1]["cache_hit"] is False
    assert payload["steps"][2]["cache_hit"] is True


def test_get_metrics_summary_returns_agentops_metrics(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.get("/metrics/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_runs"] == 1
    assert payload["task_completion_rate"] == 1.0
    assert payload["avg_latency_ms"] == 3000
    assert payload["tool_success_rate"] == 1.0
    assert payload["cache_hit_rate"] == 0.5
    assert payload["evidence_coverage"] == 1.0


def test_get_metrics_summary_handles_empty_db(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/metrics/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_runs"] == 0
    assert payload["task_completion_rate"] == 0
    assert payload["cache_hit_rate"] == 0


def _seed_agentops_run(db_path: Path) -> None:
    with connect(db_path) as conn:
        migrate(conn)
        with with_tx(conn):
            _insert_run(conn)
            EvidencesRepo().insert_many(
                [
                    EvidenceRow(
                        id="evidence-agentops",
                        run_id="run-agentops",
                        entity_id="entity-aapl",
                        source="web",
                        source_tier=2,
                        url="https://example.com/apple",
                        title="Apple evidence",
                        snippet="Apple evidence snippet.",
                        captured_at=NOW,
                        published_at=None,
                        created_at=NOW,
                    )
                ],
                conn=conn,
            )
            NodeTracesRepo().insert(
                NodeTraceRow(
                    id="trace-agentops",
                    run_id="run-agentops",
                    node_name="ingest",
                    entity_id="entity-aapl",
                    inputs_ref="state",
                    outputs_ref="success",
                    status="success",
                    reason=None,
                    fallback_used=None,
                    model_id=None,
                    evidence_ids_json='["evidence-agentops"]',
                    started_at=NOW,
                    ended_at=END,
                    created_at=NOW,
                ),
                conn=conn,
            )
            ToolInvocationsRepo().insert(
                _tool_call("tool-call-1", cache_hit=False),
                conn=conn,
            )
            ToolInvocationsRepo().insert(
                _tool_call("tool-call-2", cache_hit=True),
                conn=conn,
            )


def _insert_run(conn: sqlite3.Connection) -> None:
    RunRegistryRepo().insert(
        RunRow(
            id="run-agentops",
            position_id="position-agentops",
            entity_id="entity-aapl",
            node_kind="seed",
            status="completed",
            started_at=NOW,
            ended_at=END,
            created_at=NOW,
        ),
        conn=conn,
    )


def _tool_call(id: str, *, cache_hit: bool) -> ToolInvocationRow:
    return ToolInvocationRow(
        id=id,
        run_id="run-agentops",
        trace_id="trace-agentops",
        tool_name="search.tavily",
        status="success",
        permission_level="network",
        input_summary="query=AAPL",
        output_summary="1 docs",
        error_message=None,
        cache_key="search:AAPL",
        cache_hit=cache_hit,
        retry_count=0,
        latency_ms=120,
        token_input=0,
        token_output=0,
        estimated_cost_usd=0,
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )
