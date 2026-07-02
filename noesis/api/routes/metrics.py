from dataclasses import asdict

from fastapi import APIRouter, Depends

from noesis.agentops.metrics import build_metrics_summary
from noesis.api.deps import get_graph_deps
from noesis.api.dto import MetricsSummaryResponse
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(
    deps: GraphDeps = Depends(get_graph_deps),
) -> MetricsSummaryResponse:
    summary = build_metrics_summary(deps.repos.conn)
    return MetricsSummaryResponse(**asdict(summary))
