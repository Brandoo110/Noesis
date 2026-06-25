from typing import Literal

from pydantic import BaseModel


class PositionInput(BaseModel):
    symbol: str
    market: str
    name: str | None = None
    kind: Literal["owned", "watching"] = "owned"
    qty: float | None = None
    cost_basis: float | None = None


class ResolvedEntity(BaseModel):
    entity_id: str
    node_type: Literal["company", "segment", "theme"]
    name: str
    aliases: list[str] = []
    identifiers: dict[str, str] = {}
    market: str | None = None


class IngestedDoc(BaseModel):
    source: str
    source_tier: int
    title: str | None
    url: str | None
    text: str
    published_at: str | None = None


class EvidenceRecord(BaseModel):
    id: str
    run_id: str
    source: str
    source_tier: int
    url: str | None
    title: str | None
    snippet: str
    captured_at: str
    published_at: str | None = None


class SentimentTag(BaseModel):
    dir: Literal["up", "down", "neutral"]
    conf: float


class IntelItemDraft(BaseModel):
    title: str
    content: str
    event_type: str
    source: str
    source_tier: int
    url: str | None
    published_at: str | None
    sentiment: SentimentTag
    evidence_ids: list[str]


class ThesisAssumptionDraft(BaseModel):
    text: str
    kind: Literal["reason", "assumption", "risk"]
    evidence_ids: list[str]


class ThesisDraft(BaseModel):
    summary: str
    assumptions: list[ThesisAssumptionDraft]


class RiskFinding(BaseModel):
    code: Literal[
        "no_evidence_claim",
        "bad_basis",
        "source_backed_empty",
        "thesis_no_assumption_evidence",
    ]
    target_ref: str
    detail: str


class DegradeNote(BaseModel):
    node_name: str
    reason: str
    fallback_used: str


class ConfirmationResult(BaseModel):
    status: Literal["confirmed", "edited", "rejected"]
    edited_summary: str | None = None
    edited_assumptions: list[ThesisAssumptionDraft] | None = None
