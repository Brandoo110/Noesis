from dataclasses import dataclass
from datetime import datetime
from math import ceil
from sqlite3 import Connection, Row


@dataclass(frozen=True)
class MetricsSummary:
    total_runs: int
    task_completion_rate: float
    avg_latency_ms: int
    p95_latency_ms: int
    tool_success_rate: float
    tool_failure_rate: float
    retry_count: int
    cache_hit_rate: float
    average_token_usage: int
    estimated_cost_per_run: float
    cost_tracking_enabled: bool
    evidence_coverage: float
    unsupported_claim_count: int
    rag_retrieval_count: int


def build_metrics_summary(
    conn: Connection,
    *,
    cost_tracking_enabled: bool = True,
) -> MetricsSummary:
    runs = _run_rows(conn)
    tool_rows = _tool_rows(conn, [str(row["id"]) for row in runs])
    total_runs = len(runs)
    latencies = [_run_latency_ms(row) for row in runs]
    completed_runs = sum(1 for row in runs if row["status"] == "completed")
    evidence_run_ids = _evidence_run_ids(conn)
    return MetricsSummary(
        total_runs=total_runs,
        task_completion_rate=_ratio(completed_runs, total_runs),
        avg_latency_ms=round(sum(latencies) / len(latencies)) if latencies else 0,
        p95_latency_ms=_p95(latencies),
        tool_success_rate=_tool_status_rate(tool_rows, "success"),
        tool_failure_rate=_tool_status_rate(tool_rows, "failed"),
        retry_count=sum(int(row["retry_count"]) for row in tool_rows),
        cache_hit_rate=_ratio(
            sum(1 for row in tool_rows if int(row["cache_hit"]) == 1),
            len(tool_rows),
        ),
        average_token_usage=_average_tokens(tool_rows, total_runs),
        estimated_cost_per_run=_cost_per_run(tool_rows, total_runs),
        cost_tracking_enabled=cost_tracking_enabled,
        evidence_coverage=_ratio(
            sum(1 for row in runs if str(row["id"]) in evidence_run_ids),
            total_runs,
        ),
        unsupported_claim_count=_unsupported_claim_count(conn),
        rag_retrieval_count=sum(
            1
            for row in tool_rows
            if "retrieval" in str(row["tool_name"]) or "rag" in str(row["tool_name"])
        ),
    )


def _run_rows(conn: Connection) -> list[Row]:
    return conn.execute(
        """
        SELECT * FROM run_registry
        ORDER BY started_at, id
        """
    ).fetchall()


def _tool_rows(conn: Connection, run_ids: list[str]) -> list[Row]:
    if not run_ids:
        return []
    placeholders = ", ".join("?" for _ in run_ids)
    return conn.execute(
        f"""
        SELECT * FROM tool_invocations
        WHERE run_id IN ({placeholders})
        ORDER BY started_at, id
        """,
        tuple(run_ids),
    ).fetchall()


def _run_latency_ms(row: Row) -> int:
    ended_at = row["ended_at"]
    if ended_at is None:
        return 0
    delta = _parse_iso(str(ended_at)) - _parse_iso(str(row["started_at"]))
    return max(0, round(delta.total_seconds() * 1000))


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _tool_status_rate(rows: list[Row], status: str) -> float:
    return _ratio(sum(1 for row in rows if row["status"] == status), len(rows))


def _average_tokens(rows: list[Row], total_runs: int) -> int:
    if not rows or total_runs <= 0:
        return 0
    total = sum(int(row["token_input"]) + int(row["token_output"]) for row in rows)
    return round(total / total_runs)


def _cost_per_run(rows: list[Row], total_runs: int) -> float:
    total = sum(float(row["estimated_cost_usd"]) for row in rows)
    return round(total / total_runs, 6) if total_runs else 0.0


def _evidence_run_ids(conn: Connection) -> set[str]:
    rows = conn.execute("SELECT DISTINCT run_id FROM evidences").fetchall()
    return {str(row["run_id"]) for row in rows}


def _unsupported_claim_count(conn: Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM node_traces
        WHERE reason IN ('no_evidence_claim', 'unsupported_claim')
        """
    ).fetchone()
    return int(row["count"]) if row is not None else 0


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))
