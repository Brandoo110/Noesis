from collections import Counter

from noesis.api.dto import (
    DegradedReasonResponse,
    FailedRunResponse,
    PortfolioRunHealthResponse,
)
from noesis.api.position_rows import position_label
from noesis.db.models import NodeTraceRow, PositionRow, RunRow
from noesis.graph.state import GraphDeps


def run_health_response(
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
