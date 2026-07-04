from sqlite3 import Connection

from noesis.agentops.metrics import build_metrics_summary
from noesis.db.connection import with_tx
from noesis.db.models import ToolInvocationRow
from noesis.db.repos.tool_invocations_repo import ToolInvocationsRepo

NOW = "2026-06-26T00:00:00Z"


def test_build_metrics_summary_aggregates_runs_tools_cache_and_evidence(
    db: Connection,
) -> None:
    with with_tx(db):
        _insert_run(db, "run-fast", "completed", NOW, "2026-06-26T00:00:01Z")
        _insert_run(db, "run-slow", "failed", NOW, "2026-06-26T00:00:05Z")
        _insert_evidence(db, "evidence-1", "run-fast")
        _insert_trace(db, "trace-unsupported", "run-slow", "degraded", "no_evidence_claim")
        ToolInvocationsRepo().insert(
            _tool_invocation("tool-1", "run-fast", "success", cache_hit=True),
            conn=db,
        )
        ToolInvocationsRepo().insert(
            _tool_invocation("tool-2", "run-slow", "failed", cache_hit=False),
            conn=db,
        )

    summary = build_metrics_summary(db)

    assert summary.total_runs == 2
    assert summary.task_completion_rate == 0.5
    assert summary.avg_latency_ms == 3000
    assert summary.p95_latency_ms == 5000
    assert summary.tool_success_rate == 0.5
    assert summary.tool_failure_rate == 0.5
    assert summary.retry_count == 2
    assert summary.cache_hit_rate == 0.5
    assert summary.average_token_usage == 140
    assert summary.estimated_cost_per_run == 0.0012
    assert summary.evidence_coverage == 0.5
    assert summary.unsupported_claim_count == 1
    assert summary.rag_retrieval_count == 0


def test_average_token_usage_is_per_run_not_per_tool(db: Connection) -> None:
    with with_tx(db):
        _insert_run(db, "run-one", "completed", NOW, "2026-06-26T00:00:01Z")
        ToolInvocationsRepo().insert(
            _tool_invocation("tool-1", "run-one", "success", cache_hit=False),
            conn=db,
        )
        ToolInvocationsRepo().insert(
            _tool_invocation("tool-2", "run-one", "success", cache_hit=False),
            conn=db,
        )

    summary = build_metrics_summary(db)

    assert summary.average_token_usage == 280


def test_metrics_summary_marks_cost_tracking_availability(db: Connection) -> None:
    summary = build_metrics_summary(db, cost_tracking_enabled=False)

    assert summary.cost_tracking_enabled is False


def _insert_run(
    conn: Connection,
    run_id: str,
    status: str,
    started_at: str,
    ended_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO run_registry(
          id, position_id, entity_id, node_kind, status, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            f"position-{run_id}",
            f"entity-{run_id}",
            "seed",
            status,
            started_at,
            ended_at,
            started_at,
        ),
    )


def _insert_evidence(conn: Connection, evidence_id: str, run_id: str) -> None:
    conn.execute(
        """
        INSERT INTO evidences(
          id, run_id, entity_id, source, source_tier, url, title, snippet,
          captured_at, published_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            run_id,
            "entity-1",
            "web",
            2,
            "https://example.com",
            "Evidence",
            "Evidence snippet",
            NOW,
            None,
            NOW,
        ),
    )


def _insert_trace(
    conn: Connection,
    trace_id: str,
    run_id: str,
    status: str,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO node_traces(
          id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
          reason, fallback_used, model_id, evidence_ids_json, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id,
            run_id,
            "risk_review",
            "entity-1",
            "state",
            status,
            status,
            reason,
            "drop_invalid_claim",
            None,
            None,
            NOW,
            NOW,
            NOW,
        ),
    )


def _tool_invocation(
    id: str,
    run_id: str,
    status: str,
    *,
    cache_hit: bool,
) -> ToolInvocationRow:
    return ToolInvocationRow(
        id=id,
        run_id=run_id,
        trace_id=None,
        tool_name="search.web",
        status=status,
        permission_level="network",
        input_summary="query",
        output_summary="docs" if status == "success" else None,
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
