from typing import Literal

from pydantic import BaseModel


class CreatePositionRequest(BaseModel):
    symbol: str
    market: str
    name: str | None = None
    kind: Literal["owned", "watching"] = "owned"
    qty: float | None = None
    cost_basis: float | None = None


class PositionResponse(BaseModel):
    id: str
    symbol: str
    market: str
    name: str | None
    kind: str
    qty: float | None
    cost_basis: float | None


class CreateRunRequest(BaseModel):
    position_id: str


class RunResponse(BaseModel):
    run_id: str
    status: str
    thesis_id: str | None = None


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
    evidences: list[EvidenceResponse]
    intel_items: list[IntelItemResponse]
    thesis: ThesisResponse | None
