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
from tests.scripts.eval_fixture_helpers import seed_completed_run

END = "2026-06-26T00:00:03Z"


def test_get_runs_lists_agentops_summary(api_context: ApiTestContext) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.get("/runs")
    payload = response.json()

    assert response.status_code == 200
    assert payload["runs"] == [
        {
            "run_id": "run-agentops",
            "position_id": "position-agentops",
            "entity_id": "entity-aapl",
            "node_kind": "seed",
            "target_name": "Apple Inc.",
            "target_symbol": "AAPL",
            "target_market": "US",
            "status": "completed",
            "started_at": NOW,
            "ended_at": END,
            "latency_ms": 3000,
            "evidence_count": 1,
            "tool_count": 2,
            "cache_hit_rate": 0.5,
            "diagnostic_tags": [],
            "last_step_name": "ingest",
            "slowest_step_name": "ingest",
            "slowest_step_latency_ms": 3000,
            "has_degraded_step": False,
            "has_failed_step": False,
            "has_pending_confirmation": False,
        }
    ]


def test_get_runs_does_not_multiply_tool_counts_by_evidence_rows(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path, evidence_count=2)

    response = api_context.client.get("/runs")
    payload = response.json()

    assert response.status_code == 200
    assert payload["runs"][0]["evidence_count"] == 2
    assert payload["runs"][0]["tool_count"] == 2
    assert payload["runs"][0]["cache_hit_rate"] == 0.5


def test_get_runs_returns_diagnostic_tags(api_context: ApiTestContext) -> None:
    _seed_agentops_run(
        api_context.db_path,
        evidence_count=0,
        run_status="awaiting_confirmation",
        tool_count=0,
    )

    response = api_context.client.get("/runs")
    payload = response.json()

    assert response.status_code == 200
    summary = payload["runs"][0]
    assert summary["diagnostic_tags"] == ["waiting_confirmation", "no_tools"]
    assert summary["has_pending_confirmation"] is True
    assert summary["last_step_name"] == "ingest"
    assert summary["target_name"] == "Apple Inc."
    assert summary["target_symbol"] == "AAPL"


def test_get_runs_does_not_inherit_seed_symbol_for_expand_target(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path)
    with connect(api_context.db_path) as conn:
        with with_tx(conn):
            conn.execute(
                """
                INSERT INTO entities(
                  id, node_type, name, aliases_json, identifiers_json,
                  market, created_at, updated_at
                )
                VALUES (
                  'entity-gemini', 'company', 'Gemini Trust Company, LLC', '[]',
                  '{}', NULL, ?, ?
                )
                """,
                (NOW, NOW),
            )
            RunRegistryRepo().insert(
                RunRow(
                    id="run-expand-agentops",
                    position_id="position-agentops",
                    entity_id="entity-gemini",
                    node_kind="expand",
                    status="completed",
                    started_at="2026-06-26T00:00:04Z",
                    ended_at="2026-06-26T00:00:05Z",
                    created_at="2026-06-26T00:00:04Z",
                ),
                conn=conn,
            )

    response = api_context.client.get("/runs")
    payload = response.json()

    assert response.status_code == 200
    summary = next(
        item for item in payload["runs"] if item["run_id"] == "run-expand-agentops"
    )
    assert summary["target_name"] == "Gemini Trust Company, LLC"
    assert summary["target_symbol"] is None
    assert summary["target_market"] is None
    assert summary["node_kind"] == "expand"


def test_delete_runs_clears_run_history_but_keeps_positions_and_entities(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.delete("/runs")
    payload = response.json()

    assert response.status_code == 200
    assert payload["deleted"]["run_registry"] == 1
    assert payload["deleted"]["evidences"] == 1
    assert payload["deleted"]["tool_invocations"] == 2

    list_response = api_context.client.get("/runs")
    assert list_response.json() == {"runs": []}
    with connect(api_context.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1


def test_get_run_trace_combines_node_and_tool_timeline(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(api_context.db_path)

    response = api_context.client.get("/runs/run-agentops/trace")
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_id"] == "run-agentops"
    assert payload["status"] == "completed"
    assert payload["diagnostic"]["severity"] == "ok"
    assert payload["diagnostic"]["tags"] == []
    assert payload["diagnostic"]["slowest_step_name"] == "ingest"
    assert payload["diagnostic"]["slowest_step_latency_ms"] == 3000
    assert payload["evidence_previews"] == [
        {
            "evidence_id": "evidence-agentops-1",
            "title": "Apple evidence",
            "source": "web",
            "url": "https://example.com/apple",
            "snippet": "Apple evidence snippet.",
            "source_tier": 2,
            "published_at": None,
        }
    ]
    assert [step["kind"] for step in payload["steps"]] == ["node", "tool", "tool"]
    assert payload["steps"][0]["name"] == "ingest"
    assert payload["steps"][0]["evidence_ids"] == ["evidence-agentops-1"]
    assert payload["steps"][0]["degraded_reason"] is None
    assert payload["steps"][0]["fallback_used"] is None
    assert payload["steps"][1]["name"] == "search.tavily"
    assert payload["steps"][1]["cache_hit"] is False
    assert payload["steps"][1]["cache_key"] == "search:AAPL"
    assert payload["steps"][1]["error_message"] is None
    assert payload["steps"][1]["token_input"] == 0
    assert payload["steps"][2]["cache_hit"] is True


def test_get_run_trace_cleans_evidence_preview_snippets(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(
        api_context.db_path,
        evidence_snippet=(
            "Skip to Content\n"
            "Got a tip for us?Let us know\n"
            "a. Send us an email\n"
            "Purchase Licensing Rights ## Read Next Businesscategory Google limits "
            "Meta's use of Gemini.\n"
            "> Bloomberg corroborates The FT report today, adding that Apple is "
            "lobbying Washington and in negotiations with two Chinese companies. "
            "> Apple Inc. is in negotiations to purchase chips from two Chinese "
            "semiconductor makers to reduce the impact of a global memory shortage."
        ),
    )

    response = api_context.client.get("/runs/run-agentops/trace")
    snippet = response.json()["evidence_previews"][0]["snippet"]

    assert response.status_code == 200
    assert "Skip to Content" not in snippet
    assert "Got a tip" not in snippet
    assert "Purchase Licensing Rights" not in snippet
    assert "Read Next" not in snippet
    assert ">" not in snippet
    assert snippet == (
        "Bloomberg corroborates The FT report today, adding that Apple is "
        "lobbying Washington and in negotiations with two Chinese companies. "
        "Apple Inc. is in negotiations to purchase chips from two Chinese "
        "semiconductor makers to reduce the impact of a global memory shortage."
    )


def test_get_run_trace_diagnoses_degraded_and_failed_steps(
    api_context: ApiTestContext,
) -> None:
    _seed_agentops_run(
        api_context.db_path,
        node_status="degraded",
        node_reason="synth_llm_unavailable",
        fallback_used="no_thesis",
        tool_status="failed",
        tool_error="ReadTimeout while calling provider",
    )

    response = api_context.client.get("/runs/run-agentops/trace")
    payload = response.json()

    assert response.status_code == 200
    assert payload["diagnostic"]["severity"] == "critical"
    assert payload["diagnostic"]["tags"] == ["degraded", "failed"]
    assert "search.tavily" in payload["diagnostic"]["summary"]
    node_step = payload["steps"][0]
    tool_step = payload["steps"][1]
    assert node_step["degraded_reason"] == "synth_llm_unavailable"
    assert node_step["fallback_used"] == "no_thesis"
    assert tool_step["error_kind"] == "timeout"
    assert tool_step["error_message"] == "ReadTimeout while calling provider"


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
    assert payload["cost_currency"] == "CNY"
    assert payload["evidence_coverage"] == 1.0


def test_get_metrics_summary_handles_empty_db(api_context: ApiTestContext) -> None:
    response = api_context.client.get("/metrics/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_runs"] == 0
    assert payload["task_completion_rate"] == 0
    assert payload["cache_hit_rate"] == 0


def test_post_eval_runs_returns_eval_report(api_context: ApiTestContext) -> None:
    with connect(api_context.db_path) as conn:
        migrate(conn)
        seed_completed_run(conn)

    response = api_context.client.post("/eval/runs")
    payload = response.json()

    assert response.status_code == 200
    assert payload["mode"] == "from_db"
    assert payload["agentops"]["total_runs"] == 1
    assert payload["averages"]["grounding_rate"] == 1.0
    assert payload["cases"][0]["symbol"] == "AAPL"
    assert payload["cases"][0]["status"] == "evaluated"
    assert payload["cases"][0]["trace_summary"]["degraded"] == 1


def test_post_eval_runs_can_seed_fixture_results(api_context: ApiTestContext) -> None:
    response = api_context.client.post("/eval/runs", json={"seed_fixtures": True})
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["cases"]) >= 20
    assert {case["status"] for case in payload["cases"]} == {"evaluated"}
    assert payload["agentops"]["evidence_coverage"] == 1.0


def _seed_agentops_run(
    db_path: Path,
    *,
    evidence_count: int = 1,
    run_status: str = "completed",
    tool_count: int = 2,
    node_status: str = "success",
    node_reason: str | None = None,
    fallback_used: str | None = None,
    tool_status: str = "success",
    tool_error: str | None = None,
    evidence_snippet: str = "Apple evidence snippet.",
) -> None:
    with connect(db_path) as conn:
        migrate(conn)
        with with_tx(conn):
            conn.execute(
                """
                INSERT INTO positions(
                  id, user_id, symbol, market, name, kind,
                  qty, cost_basis, created_at, updated_at
                )
                VALUES (
                  'position-agentops', 'local-user', 'AAPL', 'US',
                  'Apple Inc.', 'owned', NULL, NULL, ?, ?
                )
                """,
                (NOW, NOW),
            )
            conn.execute(
                """
                INSERT INTO entities(
                  id, node_type, name, aliases_json, identifiers_json,
                  market, created_at, updated_at
                )
                VALUES (
                  'entity-aapl', 'company', 'Apple Inc.', '["AAPL"]',
                  '{"symbol":"AAPL"}', 'US', ?, ?
                )
                """,
                (NOW, NOW),
            )
            _insert_run(conn, status=run_status)
            EvidencesRepo().insert_many(
                [
                    EvidenceRow(
                        id=f"evidence-agentops-{index}",
                        run_id="run-agentops",
                        entity_id="entity-aapl",
                        source="web",
                        source_tier=2,
                        url="https://example.com/apple",
                        title="Apple evidence",
                        snippet=evidence_snippet,
                        captured_at=NOW,
                        published_at=None,
                        created_at=NOW,
                    )
                    for index in range(1, evidence_count + 1)
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
                    status=node_status,
                    reason=node_reason,
                    fallback_used=fallback_used,
                    model_id=None,
                    evidence_ids_json='["evidence-agentops-1"]',
                    started_at=NOW,
                    ended_at=END,
                    created_at=NOW,
                ),
                conn=conn,
            )
            for index in range(tool_count):
                ToolInvocationsRepo().insert(
                    _tool_call(
                        f"tool-call-{index + 1}",
                        cache_hit=index > 0,
                        status=tool_status if index == 0 else "success",
                        error_message=tool_error if index == 0 else None,
                    ),
                    conn=conn,
                )


def _insert_run(conn: sqlite3.Connection, *, status: str = "completed") -> None:
    RunRegistryRepo().insert(
        RunRow(
            id="run-agentops",
            position_id="position-agentops",
            entity_id="entity-aapl",
            node_kind="seed",
            status=status,
            started_at=NOW,
            ended_at=END,
            created_at=NOW,
        ),
        conn=conn,
    )


def _tool_call(
    id: str,
    *,
    cache_hit: bool,
    status: str = "success",
    error_message: str | None = None,
) -> ToolInvocationRow:
    return ToolInvocationRow(
        id=id,
        run_id="run-agentops",
        trace_id="trace-agentops",
        tool_name="search.tavily",
        status=status,
        permission_level="network",
        input_summary="query=AAPL",
        output_summary="1 docs",
        error_message=error_message,
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
