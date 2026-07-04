from typing import Literal

from pydantic import BaseModel, model_validator

from noesis.graph.schemas import ConfirmationResult, ThesisAssumptionDraft


class CreatePositionRequest(BaseModel):
    symbol: str | None = None
    market: str
    name: str | None = None
    kind: Literal["owned", "watching"] = "owned"
    qty: float | None = None
    cost_basis: float | None = None

    @model_validator(mode="after")
    def require_symbol_or_name(self) -> "CreatePositionRequest":
        symbol = self.symbol.strip() if self.symbol is not None else ""
        name = self.name.strip() if self.name is not None else ""
        if not symbol and not name:
            raise ValueError("symbol or name is required")
        return self


class PositionResponse(BaseModel):
    id: str
    symbol: str
    market: str
    name: str | None
    kind: str
    qty: float | None
    cost_basis: float | None
    latest_run_id: str | None = None
    latest_run_status: str | None = None
    latest_run_entity: "EntityNodeResponse | None" = None


class CreateRunRequest(BaseModel):
    position_id: str


class RunResponse(BaseModel):
    run_id: str
    status: str
    thesis_id: str | None = None


class RunSummaryResponse(BaseModel):
    run_id: str
    position_id: str | None
    entity_id: str | None
    node_kind: str
    target_name: str | None
    target_symbol: str | None
    target_market: str | None
    status: str
    started_at: str
    ended_at: str | None
    latency_ms: int | None
    evidence_count: int
    tool_count: int
    cache_hit_rate: float
    diagnostic_tags: list[str]
    last_step_name: str | None
    slowest_step_name: str | None
    slowest_step_latency_ms: int | None
    has_degraded_step: bool
    has_failed_step: bool
    has_pending_confirmation: bool


class RunListResponse(BaseModel):
    runs: list[RunSummaryResponse]


class ClearRunsResponse(BaseModel):
    deleted: dict[str, int]


class RunTraceStepResponse(BaseModel):
    kind: Literal["node", "tool"]
    name: str
    status: str
    started_at: str
    ended_at: str | None
    latency_ms: int | None
    input_summary: str | None
    output_summary: str | None
    cache_hit: bool | None = None
    retry_count: int | None = None
    evidence_ids: list[str]
    error_kind: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    http_status: int | None = None
    provider: str | None = None
    model_id: str | None = None
    token_input: int | None = None
    token_output: int | None = None
    estimated_cost_usd: float | None = None
    cache_key: str | None = None
    fallback_used: str | None = None
    degraded_reason: str | None = None


class RunDiagnosticResponse(BaseModel):
    severity: Literal["ok", "info", "warning", "critical"]
    title: str
    summary: str
    tags: list[str]
    slowest_step_name: str | None
    slowest_step_latency_ms: int | None
    next_actions: list[str]


class EvidencePreviewResponse(BaseModel):
    evidence_id: str
    title: str | None
    source: str
    url: str | None
    snippet: str
    source_tier: int | None
    published_at: str | None


class RunTraceResponse(BaseModel):
    run_id: str
    status: str
    diagnostic: RunDiagnosticResponse
    steps: list[RunTraceStepResponse]
    evidence_previews: list[EvidencePreviewResponse]


class MetricsSummaryResponse(BaseModel):
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


class EvalMetricsResponse(BaseModel):
    grounding_rate: float
    redline_compliance: float
    basis_honesty: float
    anchor_rate: float


class EvalTraceSummaryResponse(BaseModel):
    total: int
    started: int
    success: int
    degraded: int
    failed: int


class EvalCaseResultResponse(BaseModel):
    symbol: str
    run_id: str | None
    status: str
    metrics: EvalMetricsResponse | None
    trace_summary: EvalTraceSummaryResponse


class EvalReportResponse(BaseModel):
    mode: Literal["from_db"]
    averages: EvalMetricsResponse
    agentops: MetricsSummaryResponse
    cases: list[EvalCaseResultResponse]


class EvalRunRequest(BaseModel):
    seed_fixtures: bool = False


class ExpandRequest(BaseModel):
    position_id: str


class EntityNodeResponse(BaseModel):
    id: str
    name: str
    node_type: str
    symbol: str | None
    market: str | None


class EdgeResponse(BaseModel):
    id: str
    to_entity_id: str
    to_name: str
    to_symbol: str | None
    relation: str
    basis: Literal["inferred", "source_backed"]
    confidence: float
    evidence_ids: list[str]
    source_tier: int | None
    rationale: str | None
    neighbor: EntityNodeResponse


class ExpandResponse(BaseModel):
    entity_id: str
    run_id: str
    status: str
    edges: list[EdgeResponse]


class NeighborsResponse(BaseModel):
    entity_id: str
    edges: list[EdgeResponse]


class RelevanceResponse(BaseModel):
    entity_id: str
    position_id: str
    path: list[EntityNodeResponse]


class RepresentativeStockResponse(BaseModel):
    id: str
    name: str
    symbol: str | None


class RepresentativesResponse(BaseModel):
    segment_id: str
    representatives: list[RepresentativeStockResponse]


class OverlapPositionResponse(BaseModel):
    position_id: str
    symbol: str
    entity_id: str
    confidence: float


class OverlapGroupResponse(BaseModel):
    segment_id: str
    segment_name: str
    node_type: Literal["segment", "theme"]
    basis: Literal["inferred", "source_backed"]
    positions: list[OverlapPositionResponse]


class SharedPositionResponse(BaseModel):
    position_id: str
    symbol: str | None
    entity_id: str
    confidence: float


class SharedSupplierGroupResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    node_type: Literal["company"]
    basis: Literal["inferred", "source_backed"]
    positions: list[SharedPositionResponse]


class MatrixAxisResponse(BaseModel):
    position_id: str
    symbol: str | None
    label: str


class CorrelationCellResponse(BaseModel):
    a_position_id: str
    b_position_id: str
    shared_count: int
    shared_suppliers: list[str]


class CorrelationMatrixResponse(BaseModel):
    positions: list[MatrixAxisResponse]
    cells: list[CorrelationCellResponse]


class BriefPositionResponse(BaseModel):
    position_id: str
    symbol: str
    name: str | None
    thesis_summary: str | None
    thesis_status: str | None


class FailedRunResponse(BaseModel):
    position_id: str
    symbol: str
    run_id: str
    status: str
    reason: str | None


class DegradedReasonResponse(BaseModel):
    reason: str
    count: int


class PortfolioRunHealthResponse(BaseModel):
    total_latest_runs: int
    running: int
    awaiting_confirmation: int
    completed: int
    failed: int
    completed_without_thesis: int
    degraded_runs: int
    failed_runs: list[FailedRunResponse]
    degraded_reasons: list[DegradedReasonResponse]


class PortfolioBriefResponse(BaseModel):
    generated_at: str
    positions: list[BriefPositionResponse]
    overlaps: list[OverlapGroupResponse]
    run_health: PortfolioRunHealthResponse


class EvidenceResponse(BaseModel):
    id: str
    source: str
    source_tier: int
    url: str | None
    title: str | None
    snippet: str
    captured_at: str
    published_at: str | None


class SentimentResponse(BaseModel):
    dir: Literal["up", "down", "neutral"]
    conf: float


class IntelItemResponse(BaseModel):
    title: str
    content: str
    event_type: str
    source: str
    source_tier: int
    url: str | None
    published_at: str | None
    sentiment: SentimentResponse
    evidence_ids: list[str]


class ThesisAssumptionResponse(BaseModel):
    text: str
    kind: Literal["reason", "assumption", "risk"]
    evidence_ids: list[str]


class ThesisResponse(BaseModel):
    id: str
    summary: str
    status: str
    assumptions: list[ThesisAssumptionResponse]


class RunDetailResponse(BaseModel):
    run_id: str
    status: str
    thesis_id: str | None
    entity: EntityNodeResponse | None
    evidences: list[EvidenceResponse]
    intel_items: list[IntelItemResponse]
    thesis: ThesisResponse | None


class ConfirmAssumptionRequest(BaseModel):
    text: str
    kind: Literal["reason", "assumption", "risk"]
    evidence_ids: list[str]


class ConfirmThesisRequest(BaseModel):
    status: Literal["confirmed", "edited", "rejected"]
    edited_summary: str | None = None
    edited_assumptions: list[ConfirmAssumptionRequest] | None = None

    def to_confirmation(self) -> ConfirmationResult:
        assumptions = None
        if self.edited_assumptions is not None:
            assumptions = [
                ThesisAssumptionDraft(
                    text=item.text,
                    kind=item.kind,
                    evidence_ids=item.evidence_ids,
                )
                for item in self.edited_assumptions
            ]
        return ConfirmationResult(
            status=self.status,
            edited_summary=self.edited_summary,
            edited_assumptions=assumptions,
        )
