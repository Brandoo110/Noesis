import json
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from noesis.graph.schemas import SentimentTag

T = TypeVar("T")
JsonScalar = str | int | float | bool | None
JsonObject = dict[str, JsonScalar]

LIST_STR_ADAPTER = TypeAdapter(list[str])
DICT_STR_ADAPTER = TypeAdapter(dict[str, str])
SENTIMENT_ADAPTER = TypeAdapter(SentimentTag)
PAYLOAD_ADAPTER = TypeAdapter(JsonObject)


def _parse_json(raw: str | None, adapter: TypeAdapter[T], default: T) -> T:
    if raw is None:
        return default
    return adapter.validate_python(json.loads(raw))


class PositionRow(BaseModel):
    id: str
    user_id: str
    symbol: str
    market: str
    name: str | None
    kind: str
    qty: float | None
    cost_basis: float | None
    created_at: str
    updated_at: str


class EntityRow(BaseModel):
    id: str
    node_type: str
    name: str
    aliases_json: str
    identifiers_json: str
    market: str | None
    created_at: str
    updated_at: str

    def aliases(self) -> list[str]:
        return _parse_json(self.aliases_json, LIST_STR_ADAPTER, [])

    def identifiers(self) -> dict[str, str]:
        return _parse_json(self.identifiers_json, DICT_STR_ADAPTER, {})


class RunRow(BaseModel):
    id: str
    position_id: str | None
    entity_id: str | None
    node_kind: str
    status: str
    started_at: str
    ended_at: str | None
    created_at: str


class NodeTraceRow(BaseModel):
    id: str
    run_id: str
    node_name: str
    entity_id: str | None
    inputs_ref: str | None
    outputs_ref: str | None
    status: str
    reason: str | None
    fallback_used: str | None
    model_id: str | None
    evidence_ids_json: str | None
    started_at: str
    ended_at: str | None
    created_at: str

    def evidence_ids(self) -> list[str]:
        return _parse_json(self.evidence_ids_json, LIST_STR_ADAPTER, [])


class EvidenceRow(BaseModel):
    id: str
    run_id: str
    entity_id: str | None
    source: str
    source_tier: int
    url: str | None
    title: str | None
    snippet: str
    captured_at: str
    published_at: str | None
    created_at: str


class IntelItemRow(BaseModel):
    id: str
    entity_id: str
    run_id: str
    source: str
    source_tier: int
    title: str
    content: str
    url: str | None
    published_at: str | None
    sentiment_json: str
    event_type: str
    evidence_ids_json: str
    created_at: str

    def sentiment(self) -> SentimentTag:
        return _parse_json(self.sentiment_json, SENTIMENT_ADAPTER, None)

    def evidence_ids(self) -> list[str]:
        return _parse_json(self.evidence_ids_json, LIST_STR_ADAPTER, [])


class ThesisRow(BaseModel):
    id: str
    position_id: str
    run_id: str
    summary: str
    status: str
    created_at: str
    updated_at: str


class ThesisAssumptionRow(BaseModel):
    id: str
    thesis_id: str
    text: str
    kind: str
    evidence_ids_json: str
    status: str
    created_at: str

    def evidence_ids(self) -> list[str]:
        return _parse_json(self.evidence_ids_json, LIST_STR_ADAPTER, [])


class ApprovalRow(BaseModel):
    id: str
    run_id: str
    object_type: str
    object_id: str
    status: str
    payload_json: str | None
    created_at: str
    updated_at: str

    def payload(self) -> JsonObject:
        return _parse_json(self.payload_json, PAYLOAD_ADAPTER, {})
