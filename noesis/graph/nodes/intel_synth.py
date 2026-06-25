from pydantic import BaseModel

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.schemas import DegradeNote, EvidenceRecord, IntelItemDraft
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("evidences", "entity_id")
OUTPUT_STATE_KEYS = ("intel_items", "degraded")


class IntelSynthPayload(BaseModel):
    items: list[IntelItemDraft]


def intel_synth(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    evidences = state.get("evidences", [])
    degraded = list(state.get("degraded", []))
    if not deps.llm.available(LLMRole.LIGHT):
        degraded.append(_degrade("light_llm_unavailable", "empty_intel_items"))
        return {"intel_items": [], "degraded": degraded}
    try:
        payload = deps.llm.complete_json(
            LLMRole.LIGHT,
            _prompt(evidences),
            IntelSynthPayload,
        )
    except (LLMUnavailableError, ResearchNodeError) as exc:
        degraded.append(_degrade(exc.reason or "llm_failed", "empty_intel_items"))
        return {"intel_items": [], "degraded": degraded}
    valid_ids = {item.id for item in evidences}
    items = [
        item
        for item in payload.items
        if item.evidence_ids and set(item.evidence_ids).issubset(valid_ids)
    ]
    if len(items) != len(payload.items):
        degraded.append(_degrade("invalid_evidence_ids", "drop_invalid_intel"))
    return {"intel_items": items, "degraded": degraded}


def _prompt(evidences: list[EvidenceRecord]) -> str:
    snippets = "\n".join(
        f"- {item.id}: {item.snippet}" for item in evidences
    )
    return (
        "Extract evidence-grounded investment intelligence items. "
        "Sentiment direction means expected price-impact direction, not wording tone.\n"
        f"Evidence:\n{snippets}"
    )


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="intel_synth",
        reason=reason,
        fallback_used=fallback_used,
    )
