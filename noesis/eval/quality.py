import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Literal

QualityStatus = Literal["passed", "warning", "blocked"]
QualityFormat = Literal["text", "json", "markdown"]


@dataclass(frozen=True)
class QualityReport:
    status: QualityStatus
    total_positions: int
    latest_seed_runs: int
    status_counts: dict[str, int]
    evidence_total: int
    source_tier_counts: dict[int, int]
    runs_without_evidence: tuple[str, ...]
    runs_without_thesis: tuple[str, ...]
    completed_runs_without_evidence: tuple[str, ...]
    completed_runs_without_thesis: tuple[str, ...]
    pending_runs_without_evidence: tuple[str, ...]
    pending_runs_without_thesis: tuple[str, ...]
    degraded_reason_counts: dict[str, int]
    failed_runs: tuple[tuple[str, str, str | None], ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def build_quality_report(conn: sqlite3.Connection) -> QualityReport:
    positions = _local_positions(conn)
    latest_runs = _latest_seed_runs(conn)
    run_ids = [str(run["id"]) for run in latest_runs]
    evidence_counts = _evidence_counts(conn, run_ids)
    thesis_run_ids = _thesis_run_ids(conn, run_ids)
    traces = _traces(conn, run_ids)
    failed_reason_by_run = _failed_reason_by_run(traces)

    status_counts = Counter(str(run["status"]) for run in latest_runs)
    evidence_total = sum(evidence_counts.values())
    source_tier_counts = Counter(_source_tiers(conn, run_ids))
    runs_without_evidence = tuple(
        str(run["id"]) for run in latest_runs if evidence_counts.get(str(run["id"]), 0) == 0
    )
    runs_without_thesis = tuple(
        str(run["id"]) for run in latest_runs if str(run["id"]) not in thesis_run_ids
    )
    completed_runs_without_evidence = tuple(
        str(run["id"])
        for run in latest_runs
        if run["status"] == "completed" and evidence_counts.get(str(run["id"]), 0) == 0
    )
    completed_runs_without_thesis = tuple(
        str(run["id"])
        for run in latest_runs
        if run["status"] == "completed" and str(run["id"]) not in thesis_run_ids
    )
    pending_runs_without_evidence = tuple(
        str(run["id"])
        for run in latest_runs
        if _is_pending_status(str(run["status"]))
        and evidence_counts.get(str(run["id"]), 0) == 0
    )
    pending_runs_without_thesis = tuple(
        str(run["id"])
        for run in latest_runs
        if _is_pending_status(str(run["status"])) and str(run["id"]) not in thesis_run_ids
    )
    degraded_reason_counts = Counter(
        str(trace["reason"] or "unknown")
        for trace in traces
        if trace["status"] == "degraded"
    )
    failed_runs = tuple(
        (
            str(run["symbol"] or ""),
            str(run["id"]),
            failed_reason_by_run.get(str(run["id"])),
        )
        for run in latest_runs
        if run["status"] == "failed"
    )
    blockers = _blockers(
        status_counts=status_counts,
        completed_runs_without_evidence=completed_runs_without_evidence,
        completed_runs_without_thesis=completed_runs_without_thesis,
    )
    warnings = _warnings(
        total_positions=len(positions),
        latest_seed_runs=len(latest_runs),
        pending_runs_without_evidence=pending_runs_without_evidence,
        pending_runs_without_thesis=pending_runs_without_thesis,
        degraded_reason_counts=degraded_reason_counts,
    )
    return QualityReport(
        status=_status(blockers, warnings),
        total_positions=len(positions),
        latest_seed_runs=len(latest_runs),
        status_counts=dict(sorted(status_counts.items())),
        evidence_total=evidence_total,
        source_tier_counts=dict(sorted(source_tier_counts.items())),
        runs_without_evidence=runs_without_evidence,
        runs_without_thesis=runs_without_thesis,
        completed_runs_without_evidence=completed_runs_without_evidence,
        completed_runs_without_thesis=completed_runs_without_thesis,
        pending_runs_without_evidence=pending_runs_without_evidence,
        pending_runs_without_thesis=pending_runs_without_thesis,
        degraded_reason_counts=dict(sorted(degraded_reason_counts.items())),
        failed_runs=failed_runs,
        blockers=blockers,
        warnings=warnings,
    )


def format_quality_report(
    report: QualityReport,
    *,
    output_format: QualityFormat = "text",
) -> str:
    from noesis.eval.quality_format import format_quality_payload

    return format_quality_payload(report, output_format=output_format)


def _local_positions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM positions
        WHERE user_id = 'local-user'
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()


def _latest_seed_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        WITH ranked AS (
          SELECT
            run_registry.*,
            positions.symbol AS symbol,
            ROW_NUMBER() OVER (
              PARTITION BY run_registry.position_id
              ORDER BY run_registry.started_at DESC,
                       run_registry.created_at DESC,
                       run_registry.id DESC
            ) AS rn
          FROM run_registry
          JOIN positions ON positions.id = run_registry.position_id
          WHERE positions.user_id = 'local-user'
            AND run_registry.node_kind = 'seed'
        )
        SELECT * FROM ranked
        WHERE rn = 1
        ORDER BY started_at DESC, created_at DESC, id DESC
        """
    ).fetchall()


def _evidence_counts(conn: sqlite3.Connection, run_ids: list[str]) -> dict[str, int]:
    if not run_ids:
        return {}
    placeholders = ", ".join("?" for _ in run_ids)
    rows = conn.execute(
        f"""
        SELECT run_id, COUNT(*) AS count
        FROM evidences
        WHERE run_id IN ({placeholders})
        GROUP BY run_id
        """,
        tuple(run_ids),
    ).fetchall()
    return {str(row["run_id"]): int(row["count"]) for row in rows}


def _source_tiers(conn: sqlite3.Connection, run_ids: list[str]) -> list[int]:
    if not run_ids:
        return []
    placeholders = ", ".join("?" for _ in run_ids)
    rows = conn.execute(
        f"""
        SELECT source_tier
        FROM evidences
        WHERE run_id IN ({placeholders})
        ORDER BY source_tier
        """,
        tuple(run_ids),
    ).fetchall()
    return [int(row["source_tier"]) for row in rows]


def _thesis_run_ids(conn: sqlite3.Connection, run_ids: list[str]) -> set[str]:
    if not run_ids:
        return set()
    placeholders = ", ".join("?" for _ in run_ids)
    rows = conn.execute(
        f"""
        SELECT run_id
        FROM theses
        WHERE run_id IN ({placeholders})
        """,
        tuple(run_ids),
    ).fetchall()
    return {str(row["run_id"]) for row in rows}


def _traces(conn: sqlite3.Connection, run_ids: list[str]) -> list[sqlite3.Row]:
    if not run_ids:
        return []
    placeholders = ", ".join("?" for _ in run_ids)
    return conn.execute(
        f"""
        SELECT *
        FROM node_traces
        WHERE run_id IN ({placeholders})
        ORDER BY started_at, id
        """,
        tuple(run_ids),
    ).fetchall()


def _failed_reason_by_run(traces: list[sqlite3.Row]) -> dict[str, str | None]:
    reasons: dict[str, str | None] = {}
    for trace in traces:
        if trace["status"] == "failed":
            reasons[str(trace["run_id"])] = (
                str(trace["reason"]) if trace["reason"] is not None else None
            )
    return reasons


def _is_pending_status(status: str) -> bool:
    return status not in {"completed", "failed"}


def _status(blockers: tuple[str, ...], warnings: tuple[str, ...]) -> QualityStatus:
    if blockers:
        return "blocked"
    if warnings:
        return "warning"
    return "passed"


def _blockers(
    *,
    status_counts: Counter[str],
    completed_runs_without_evidence: tuple[str, ...],
    completed_runs_without_thesis: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if status_counts.get("failed", 0) > 0:
        blockers.append(f"failed latest runs: {status_counts['failed']}")
    if completed_runs_without_evidence:
        blockers.append(
            f"completed runs without evidence: {len(completed_runs_without_evidence)}"
        )
    if completed_runs_without_thesis:
        blockers.append(
            f"completed runs without thesis: {len(completed_runs_without_thesis)}"
        )
    return tuple(blockers)


def _warnings(
    *,
    total_positions: int,
    latest_seed_runs: int,
    pending_runs_without_evidence: tuple[str, ...],
    pending_runs_without_thesis: tuple[str, ...],
    degraded_reason_counts: Counter[str],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if total_positions == 0:
        warnings.append("no local-user positions")
    if latest_seed_runs == 0:
        warnings.append("no latest seed runs")
    if pending_runs_without_evidence:
        warnings.append(
            f"pending runs without evidence: {len(pending_runs_without_evidence)}"
        )
    if pending_runs_without_thesis:
        warnings.append(
            f"pending runs without thesis: {len(pending_runs_without_thesis)}"
        )
    if degraded_reason_counts:
        warnings.append(f"degraded latest runs: {sum(degraded_reason_counts.values())}")
    return tuple(warnings)
