from collections import Counter

from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    BriefPositionResponse,
    DegradedReasonResponse,
    FailedRunResponse,
    OverlapGroupResponse,
    OverlapPositionResponse,
    PortfolioBriefResponse,
    PortfolioRunHealthResponse,
)
from noesis.api.position_rows import dedupe_positions, position_label
from noesis.db.models import NodeTraceRow, PositionRow, RunRow
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import OverlapGroup, portfolio_overlap

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overlaps", response_model=list[OverlapGroupResponse])
def get_portfolio_overlaps(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[OverlapGroupResponse]:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    return [
        _overlap_response(group)
        for group in _portfolio_overlap_groups(deps, positions)
    ]


@router.get("/brief", response_model=PortfolioBriefResponse)
def get_portfolio_brief(
    deps: GraphDeps = Depends(get_graph_deps),
) -> PortfolioBriefResponse:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    return PortfolioBriefResponse(
        generated_at=deps.now(),
        positions=[_brief_position_response(position, deps) for position in positions],
        overlaps=[
            _overlap_response(group)
            for group in _portfolio_overlap_groups(deps, positions)
        ],
        run_health=_run_health_response(deps, positions),
    )


def _portfolio_overlap_groups(
    deps: GraphDeps, positions: list[PositionRow]
) -> list[OverlapGroup]:
    return portfolio_overlap(
        _positions_with_seed(deps, positions),
        deps.repos.graph_edges,
        deps.repos.entities,
    )


def _positions_with_seed(
    deps: GraphDeps, positions: list[PositionRow]
) -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    for position in positions:
        seed_entity_id = deps.repos.runs.get_seed_entity_id(position.id)
        if seed_entity_id is not None:
            values.append((position.id, position_label(position), seed_entity_id))
    return values


def _brief_position_response(
    position: PositionRow, deps: GraphDeps
) -> BriefPositionResponse:
    thesis = deps.repos.theses.latest_for_position(position.id)
    return BriefPositionResponse(
        position_id=position.id,
        symbol=position_label(position),
        name=position.name,
        thesis_summary=thesis.summary if thesis is not None else None,
        thesis_status=thesis.status if thesis is not None else None,
    )


def _overlap_response(group: OverlapGroup) -> OverlapGroupResponse:
    return OverlapGroupResponse(
        segment_id=group.segment_id,
        segment_name=group.segment_name,
        node_type=group.node_type,
        basis=group.basis,
        positions=[
            OverlapPositionResponse(
                position_id=position.position_id,
                symbol=position.symbol,
                entity_id=position.entity_id,
                confidence=position.confidence,
            )
            for position in group.positions
        ],
    )


def _run_health_response(
    deps: GraphDeps, positions: list[PositionRow]
) -> PortfolioRunHealthResponse:
    latest_runs = deps.repos.runs.latest_seed_for_positions(
        [position.id for position in positions]
    )
    run_ids = [run.id for run in latest_runs]
    traces = deps.repos.traces.list_by_run_ids(run_ids)
    thesis_run_ids = {item.run_id for item in deps.repos.theses.list_by_run_ids(run_ids)}
    traces_by_run = _traces_by_run(traces)
    degraded_reasons = Counter(
        trace.reason or "unknown"
        for trace in traces
        if trace.status == "degraded"
    )
    return PortfolioRunHealthResponse(
        total_latest_runs=len(latest_runs),
        running=_status_count(latest_runs, "running"),
        awaiting_confirmation=_status_count(latest_runs, "awaiting_confirmation"),
        completed=_status_count(latest_runs, "completed"),
        failed=_status_count(latest_runs, "failed"),
        completed_without_thesis=sum(
            1
            for run in latest_runs
            if run.status == "completed" and run.id not in thesis_run_ids
        ),
        degraded_runs=len(
            {
                trace.run_id
                for trace in traces
                if trace.status == "degraded"
            }
        ),
        failed_runs=_failed_run_responses(positions, latest_runs, traces_by_run),
        degraded_reasons=[
            DegradedReasonResponse(reason=reason, count=count)
            for reason, count in sorted(degraded_reasons.items())
        ],
    )


def _status_count(runs: list[RunRow], status: str) -> int:
    return sum(1 for run in runs if run.status == status)


def _traces_by_run(traces: list[NodeTraceRow]) -> dict[str, list[NodeTraceRow]]:
    values: dict[str, list[NodeTraceRow]] = {}
    for trace in traces:
        values.setdefault(trace.run_id, []).append(trace)
    return values


def _failed_run_responses(
    positions: list[PositionRow],
    latest_runs: list[RunRow],
    traces_by_run: dict[str, list[NodeTraceRow]],
) -> list[FailedRunResponse]:
    positions_by_id = {position.id: position for position in positions}
    failed_runs = [run for run in latest_runs if run.status == "failed"]
    return [
        FailedRunResponse(
            position_id=run.position_id or "",
            symbol=position_label(positions_by_id[run.position_id])
            if run.position_id in positions_by_id
            else "",
            run_id=run.id,
            status=run.status,
            reason=_failed_reason(traces_by_run.get(run.id, [])),
        )
        for run in failed_runs
    ]


def _failed_reason(traces: list[NodeTraceRow]) -> str | None:
    for trace in traces:
        if trace.status == "failed":
            return trace.reason
    return None
