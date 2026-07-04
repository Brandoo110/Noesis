from dataclasses import asdict

from fastapi import APIRouter, Depends

from noesis.agentops.metrics import build_metrics_summary
from noesis.api.deps import get_graph_deps
from noesis.api.dto import MetricsSummaryResponse
from noesis.config.settings import Settings, get_settings
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(
    deps: GraphDeps = Depends(get_graph_deps),
    settings: Settings = Depends(get_settings),
) -> MetricsSummaryResponse:
    summary = build_metrics_summary(
        deps.repos.conn,
        cost_tracking_enabled=_cost_tracking_enabled(settings),
        cost_currency=settings.llm_cost_currency,
        cost_rates=_cost_rates(settings),
    )
    return MetricsSummaryResponse(**asdict(summary))


def _cost_tracking_enabled(settings: Settings) -> bool:
    return any(
        value > 0
        for value in (
            settings.light_input_cost_per_million,
            settings.light_output_cost_per_million,
            settings.deepseek_input_cost_per_million,
            settings.deepseek_output_cost_per_million,
            settings.risk_input_cost_per_million,
            settings.risk_output_cost_per_million,
        )
    )


def _cost_rates(settings: Settings) -> dict[str, tuple[float, float]]:
    return {
        "llm.light": (
            settings.light_input_cost_per_million,
            settings.light_output_cost_per_million,
        ),
        "llm.synth": (
            settings.deepseek_input_cost_per_million_at(),
            settings.deepseek_output_cost_per_million_at(),
        ),
        "llm.risk": (
            settings.risk_input_cost_per_million,
            settings.risk_output_cost_per_million,
        ),
    }
