from dataclasses import asdict

from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    EvalCaseResultResponse,
    EvalMetricsResponse,
    EvalReportResponse,
    EvalRunRequest,
    EvalTraceSummaryResponse,
    MetricsSummaryResponse,
)
from noesis.eval.cases import EVAL_CASES
from noesis.eval.fixtures import seed_eval_fixture_runs
from noesis.eval.report import EvalCaseResult, EvalReport
from noesis.eval.runner import evaluate_existing_runs
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/runs", response_model=EvalReportResponse)
def run_eval_from_db(
    request: EvalRunRequest | None = None,
    deps: GraphDeps = Depends(get_graph_deps),
) -> EvalReportResponse:
    if request is not None and request.seed_fixtures:
        seed_eval_fixture_runs(EVAL_CASES, deps)
    return _report_response(evaluate_existing_runs(EVAL_CASES, deps))


@router.get("/latest", response_model=EvalReportResponse)
def get_latest_eval_report(
    deps: GraphDeps = Depends(get_graph_deps),
) -> EvalReportResponse:
    return _report_response(evaluate_existing_runs(EVAL_CASES, deps))


def _report_response(report: EvalReport) -> EvalReportResponse:
    return EvalReportResponse(
        mode="from_db",
        averages=EvalMetricsResponse(**report.averages),
        agentops=MetricsSummaryResponse(**asdict(report.agentops)),
        cases=[_case_response(result) for result in report.results],
    )


def _case_response(result: EvalCaseResult) -> EvalCaseResultResponse:
    return EvalCaseResultResponse(
        symbol=result.symbol,
        run_id=result.run_id,
        status=result.status,
        metrics=(
            EvalMetricsResponse(**result.metrics)
            if result.metrics is not None
            else None
        ),
        trace_summary=EvalTraceSummaryResponse(**result.trace_summary),
    )
