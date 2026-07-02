from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Literal, cast

from noesis.agentops.metrics import build_metrics_summary
from noesis.db.models import EntityRow, EvidenceRow, GraphEdgeRow, RunRow
from noesis.eval.cases import EvalCase
from noesis.eval.metrics import EvalMetrics, evaluate_run
from noesis.eval.report import (
    EvalCaseResult,
    EvalReport,
    empty_trace_summary,
    trace_summary,
)
from noesis.graph.runner import get_run_snapshot
from noesis.graph.schemas import EvidenceRecord, GraphEdgeDraft, ResolvedEntity
from noesis.graph.state import GraphDeps


def evaluate_existing_runs(
    cases: Sequence[EvalCase], deps: GraphDeps
) -> EvalReport:
    results: list[EvalCaseResult] = []
    for case in cases:
        run = _latest_seed_run(case, deps.repos.conn)
        if run is None:
            results.append(
                EvalCaseResult(
                    symbol=case.symbol,
                    run_id=None,
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


def _latest_seed_run(case: EvalCase, conn: sqlite3.Connection) -> RunRow | None:
    row = conn.execute(
        """
        SELECT run_registry.* FROM run_registry
        JOIN positions ON positions.id = run_registry.position_id
        WHERE upper(positions.symbol) = ?
          AND positions.market = ?
          AND run_registry.node_kind = 'seed'
        ORDER BY run_registry.started_at DESC, run_registry.created_at DESC,
                 run_registry.id DESC
        LIMIT 1
        """,
        (case.symbol.upper(), case.market),
    ).fetchone()
    return RunRow.model_validate(dict(row)) if row is not None else None


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
    return [
        _edge_from_row(row, deps)
        for row in deps.repos.graph_edges.list_from(entity_id)
    ]


def _edge_from_row(row: GraphEdgeRow, deps: GraphDeps) -> GraphEdgeDraft:
    to_entity = deps.repos.entities.get(row.to_entity_id)
    to_name = to_entity.name if to_entity is not None else row.to_entity_id
    to_symbol = to_entity.identifiers().get("symbol") if to_entity is not None else None
    to_node_type = to_entity.node_type if to_entity is not None else "company"
    return GraphEdgeDraft(
        to_name=to_name,
        to_symbol=to_symbol,
        to_node_type=cast(Literal["company", "segment", "theme"], to_node_type),
        relation=cast(
            Literal["supplier", "customer", "competitor", "belongs_to"],
            row.relation,
        ),
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
        for key in (
            "grounding_rate",
            "redline_compliance",
            "basis_honesty",
            "anchor_rate",
        )
    }
