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


class BriefPositionResponse(BaseModel):
    position_id: str
    symbol: str
    name: str | None
    thesis_summary: str | None
    thesis_status: str | None


class PortfolioBriefResponse(BaseModel):
    generated_at: str
    positions: list[BriefPositionResponse]
    overlaps: list[OverlapGroupResponse]


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
