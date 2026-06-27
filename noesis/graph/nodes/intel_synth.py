from pydantic import BaseModel

from noesis.db.models import EntityRow
from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.schemas import (
    DegradeNote,
    EvidenceRecord,
    IntelItemDraft,
    ResolvedEntity,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("evidences", "entity_id", "resolved_entity")
OUTPUT_STATE_KEYS = ("intel_items", "degraded")


class IntelSynthPayload(BaseModel):
    items: list[IntelItemDraft]


def intel_synth(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    evidences = state.get("evidences", [])
    degraded = list(state.get("degraded", []))
    target = _resolve_target(state, deps)
    if target is None:
        degraded.append(_degrade("target_unresolved", "unanchored_intel_prompt"))
    if not deps.llm.available(LLMRole.LIGHT):
        degraded.append(_degrade("light_llm_unavailable", "empty_intel_items"))
        return {"intel_items": [], "degraded": degraded}
    try:
        payload = deps.llm.complete_json(
            LLMRole.LIGHT,
            _prompt(evidences, target),
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


def _resolve_target(state: ResearchState, deps: GraphDeps) -> ResolvedEntity | None:
    target = state.get("resolved_entity")
    if target is not None:
        return target
    entity_id = state.get("entity_id")
    if entity_id is None:
        return None
    entities_repo = getattr(deps.repos, "entities", None)
    if entities_repo is None:
        return None
    row = entities_repo.get(entity_id)
    if row is None:
        return None
    return _target_from_row(row)


def _target_from_row(row: EntityRow) -> ResolvedEntity:
    return ResolvedEntity(
        entity_id=row.id,
        node_type=row.node_type,
        name=row.name,
        aliases=row.aliases(),
        identifiers=row.identifiers(),
        market=row.market,
    )


def _prompt(evidences: list[EvidenceRecord], target: ResolvedEntity | None) -> str:
    snippets = "\n".join(
        f"- {item.id}: {item.snippet}" for item in evidences
    )
    target_clause = _target_clause(target)
    return (
        "Extract evidence-grounded investment intelligence items. "
        f"{target_clause}"
        "Sentiment direction means expected price-impact direction, not wording tone.\n"
        f"Evidence:\n{snippets}"
    )


def _target_clause(target: ResolvedEntity | None) -> str:
    if target is None:
        return "Target entity is unresolved; do not infer a target from unrelated evidence. "
    symbol = target.identifiers.get("symbol", "unknown")
    aliases = ", ".join(target.aliases) if target.aliases else "none"
    return (
        "Only extract intelligence whose PRIMARY SUBJECT is the target company: "
        f"{target.name} (symbol {symbol}, aliases {aliases}). "
        "If an evidence snippet's main subject is a DIFFERENT company, even one "
        "mentioned alongside the target, DISCARD it. "
        "Prefer the target's fundamentals, products, supply chain, partnerships, "
        "and material events over generic share-price movements of other firms. "
        "Do not recommend buying or selling and do not predict prices. "
    )


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="intel_synth",
        reason=reason,
        fallback_used=fallback_used,
    )
