"""Run Noesis research quality evaluation.

Default mode is offline: read existing runs from the configured SQLite DB and
print quality metrics. Use --live only when you intentionally want to call real
search/LLM providers.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noesis.config.settings import Settings
from noesis.agentops.metrics import build_metrics_summary
from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, EvidenceRow, GraphEdgeRow, PositionRow, RunRow
from noesis.eval.cases import EVAL_CASES, EvalCase
from noesis.eval.metrics import EvalMetrics, evaluate_run
from noesis.eval.report import (
    EvalCaseResult,
    EvalMode,
    EvalReport,
    ReportFormat,
    empty_trace_summary,
    format_report,
    trace_summary,
)
from noesis.eval.runner import evaluate_existing_runs as evaluate_existing_runs_from_db
from noesis.graph.runner import build_graph_deps, get_run_snapshot, start_run
from noesis.graph.schemas import EvidenceRecord, GraphEdgeDraft, PositionInput, ResolvedEntity
from noesis.graph.state import GraphDeps
from noesis.tools.llm.router import LLMRouter
from noesis.tools.search.tavily import TavilySearchAdapter


@dataclass(frozen=True)
class EvalArgs:
    from_db: bool
    db_path: str | None
    format: ReportFormat


@dataclass(frozen=True)
class EvalRuntime:
    deps: GraphDeps
    conn: sqlite3.Connection
    checkpoint_conn: sqlite3.Connection


def parse_args(argv: Sequence[str] | None = None) -> EvalArgs:
    parser = argparse.ArgumentParser(description="Run Noesis eval metrics.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--from-db", dest="from_db", action="store_true", default=True)
    mode.add_argument("--live", dest="from_db", action="store_false")
    parser.add_argument("--db-path", default=None)
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Report format for local review, CI, or evidence packages.",
    )
    parsed = parser.parse_args(argv)
    return EvalArgs(
        from_db=bool(parsed.from_db),
        db_path=parsed.db_path,
        format=cast(ReportFormat, parsed.format),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    settings = Settings()
    db_path = args.db_path or settings.db_path
    with runtime(settings, db_path) as current:
        report = (
            evaluate_existing_runs(EVAL_CASES, current.deps)
            if args.from_db
            else evaluate_live_runs(EVAL_CASES, current.deps)
        )
    mode: EvalMode = "from_db" if args.from_db else "live"
    print(format_report(report, mode=mode, output_format=args.format))
    return 0


def evaluate_existing_runs(
    cases: Sequence[EvalCase], deps: GraphDeps
) -> EvalReport:
    return evaluate_existing_runs_from_db(cases, deps)


def evaluate_live_runs(cases: Sequence[EvalCase], deps: GraphDeps) -> EvalReport:
    results: list[EvalCaseResult] = []
    for case in cases:
        position_id = _ensure_position(case, deps)
        handle = start_run(position_id, deps)
        run = deps.repos.runs.get(handle.run_id)
        if run is None:
            results.append(
                EvalCaseResult(
                    symbol=case.symbol,
                    run_id=handle.run_id,
                    status="missing",
                    metrics=None,
                    trace_summary=empty_trace_summary(),
                )
            )
            continue
        results.append(_evaluate_run_row(case, run, deps))
    return EvalReport(
        results=tuple(results),
        averages=_average_metrics(results),
        agentops=build_metrics_summary(deps.repos.conn),
    )


@contextmanager
def runtime(settings: Settings, db_path: str) -> Iterator[EvalRuntime]:
    conn = connect(db_path)
    checkpoint_conn = sqlite3.connect(_checkpoint_path(db_path), check_same_thread=False)
    try:
        migrate(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=settings.chroma_dir,
            search=TavilySearchAdapter(settings.tavily_api_key),
            llm=LLMRouter.from_env(settings),
            now=_utc_now,
        )
        yield EvalRuntime(deps=deps, conn=conn, checkpoint_conn=checkpoint_conn)
    finally:
        checkpoint_conn.close()
        conn.close()


def _evaluate_run_row(case: EvalCase, run: RunRow, deps: GraphDeps) -> EvalCaseResult:
    snapshot = get_run_snapshot(run.id, deps)
    target = snapshot.resolved_entity or _target_from_case(case, run.entity_id, deps)
    entity_id = run.entity_id or target.entity_id
    edges = _edges_for_entity(entity_id, deps) if entity_id else []
    metrics = evaluate_run(
        snapshot.intel_items,
        snapshot.thesis_draft,
        edges,
        snapshot.evidences,
        target,
        edge_evidences=_evidences_for_edges(edges, deps),
    )
    return EvalCaseResult(
        symbol=case.symbol,
        run_id=run.id,
        status="evaluated",
        metrics=metrics,
        trace_summary=trace_summary(run.id, deps),
    )


def _ensure_position(case: EvalCase, deps: GraphDeps) -> str:
    row = deps.repos.conn.execute(
        """
        SELECT * FROM positions
        WHERE user_id = 'local-user' AND upper(symbol) = ? AND market = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (case.symbol.upper(), case.market),
    ).fetchone()
    if row is not None:
        return str(row["id"])
    position_id = f"position-{uuid4().hex}"
    now = deps.now()
    with with_tx(deps.repos.conn):
        deps.repos.positions.insert(
            PositionRow(
                id=position_id,
                user_id="local-user",
                symbol=case.symbol,
                market=case.market,
                name=case.name,
                kind="owned",
                qty=None,
                cost_basis=None,
                created_at=now,
                updated_at=now,
            )
        )
    return position_id


def _target_from_case(
    case: EvalCase, entity_id: str | None, deps: GraphDeps
) -> ResolvedEntity:
    row = deps.repos.entities.get(entity_id) if entity_id else None
    if row is not None:
        return _target_from_entity(row)
    return ResolvedEntity(
        entity_id=entity_id or "",
        node_type="company",
        name=case.name,
        aliases=[case.symbol],
        identifiers={"symbol": case.symbol},
        market=case.market,
    )


def _target_from_entity(row: EntityRow) -> ResolvedEntity:
    return ResolvedEntity(
        entity_id=row.id,
        node_type=cast(Literal["company", "segment", "theme"], row.node_type),
        name=row.name,
        aliases=row.aliases(),
        identifiers=row.identifiers(),
        market=row.market,
    )


def _edges_for_entity(entity_id: str, deps: GraphDeps) -> list[GraphEdgeDraft]:
    return [_edge_from_row(row, deps) for row in deps.repos.graph_edges.list_from(entity_id)]


def _edge_from_row(row: GraphEdgeRow, deps: GraphDeps) -> GraphEdgeDraft:
    to_entity = deps.repos.entities.get(row.to_entity_id)
    to_name = to_entity.name if to_entity is not None else row.to_entity_id
    to_symbol = to_entity.identifiers().get("symbol") if to_entity is not None else None
    to_node_type = to_entity.node_type if to_entity is not None else "company"
    return GraphEdgeDraft(
        to_name=to_name,
        to_symbol=to_symbol,
        to_node_type=cast(Literal["company", "segment", "theme"], to_node_type),
        relation=cast(Literal["supplier", "customer", "competitor", "belongs_to"], row.relation),
        basis=cast(Literal["inferred", "source_backed"], row.basis),
        confidence=row.confidence,
        evidence_ids=row.evidence_ids(),
        rationale=row.rationale or "",
    )


def _evidences_for_edges(
    edges: Sequence[GraphEdgeDraft], deps: GraphDeps
) -> list[EvidenceRecord]:
    evidence_ids = {
        evidence_id
        for edge in edges
        for evidence_id in edge.evidence_ids
    }
    records: list[EvidenceRecord] = []
    for evidence_id in sorted(evidence_ids):
        row = deps.repos.evidences.get(evidence_id, conn=deps.repos.conn)
        if row is not None:
            records.append(_evidence_from_row(row))
    return records


def _evidence_from_row(row: EvidenceRow) -> EvidenceRecord:
    return EvidenceRecord(
        id=row.id,
        run_id=row.run_id,
        source=row.source,
        source_tier=row.source_tier,
        url=row.url,
        title=row.title,
        snippet=row.snippet,
        captured_at=row.captured_at,
        published_at=row.published_at,
    )


def _average_metrics(results: Sequence[EvalCaseResult]) -> EvalMetrics:
    metrics = [result.metrics for result in results if result.metrics is not None]
    if not metrics:
        return {
            "grounding_rate": 0.0,
            "redline_compliance": 0.0,
            "basis_honesty": 0.0,
            "anchor_rate": 0.0,
        }
    return {
        key: sum(item[key] for item in metrics) / len(metrics)
        for key in ("grounding_rate", "redline_compliance", "basis_honesty", "anchor_rate")
    }


def _checkpoint_path(db_path: str) -> str:
    path = Path(db_path)
    if path.suffix:
        return str(path.with_suffix(f"{path.suffix}.checkpoints"))
    return f"{db_path}.checkpoints"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
