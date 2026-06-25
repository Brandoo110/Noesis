from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.schemas import (
    DegradeNote,
    EvidenceRecord,
    IntelItemDraft,
    ResolvedEntity,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("position_id", "resolved_entity", "intel_items", "evidences")
OUTPUT_STATE_KEYS = ("thesis_draft", "degraded")
PROHIBITED_TERMS = (
    "buy",
    "sell",
    "price target",
    "target price",
    "predict stock price",
    "买入",
    "卖出",
    "目标价",
    "预测股价",
)


def thesis_draft(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    degraded = list(state.get("degraded", []))
    intel_items = state.get("intel_items", [])
    if not intel_items:
        degraded.append(_degrade("no_intel_for_thesis", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    if not deps.llm.available(LLMRole.SYNTH):
        degraded.append(_degrade("synth_llm_unavailable", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    try:
        draft = deps.llm.complete_json(
            LLMRole.SYNTH,
            _prompt(
                state.get("resolved_entity"),
                intel_items,
                state.get("evidences", []),
            ),
            ThesisDraft,
        )
    except (LLMUnavailableError, ResearchNodeError) as exc:
        degraded.append(_degrade(exc.reason or "llm_failed", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    valid_ids = {item.id for item in state.get("evidences", [])}
    if not _valid_draft(draft, valid_ids, state.get("resolved_entity")):
        degraded.append(_degrade("invalid_or_unsafe_thesis", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    return {"thesis_draft": draft, "degraded": degraded}


def _prompt(
    target: ResolvedEntity | None,
    intel_items: list[IntelItemDraft],
    evidences: list[EvidenceRecord],
) -> str:
    intel_text = "\n".join(f"- {item.title}: {item.content}" for item in intel_items)
    evidence_text = "\n".join(f"- {item.id}: {item.snippet}" for item in evidences)
    return (
        "Draft a research thesis for confirmation. Do not recommend buying, "
        "selling, trading, price targets, or stock-price predictions. "
        "The target entity is locked; summary and every assumption must use "
        "the target company itself as the subject. If evidence mainly discusses "
        "another company, cite it only as an impact on the target company. "
        "Every assumption must cite provided evidence ids.\n"
        f"Target entity: symbol={_target_symbol(target)}; "
        f"market={target.market if target and target.market else 'unknown'}; "
        f"name={target.name if target else ''}\n"
        f"Intel:\n{intel_text}\nEvidence:\n{evidence_text}"
    )


def _valid_draft(
    draft: ThesisDraft,
    valid_ids: set[str],
    target: ResolvedEntity | None,
) -> bool:
    if _has_redline_text(draft.summary) or not draft.assumptions:
        return False
    if target is not None and not _mentions_target(draft.summary, target):
        return False
    for assumption in draft.assumptions:
        if _has_redline_text(assumption.text):
            return False
        if not assumption.evidence_ids or not set(assumption.evidence_ids).issubset(valid_ids):
            return False
    return True


def _has_redline_text(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in PROHIBITED_TERMS)


def _mentions_target(text: str, target: ResolvedEntity) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in _target_terms(target))


def _target_terms(target: ResolvedEntity) -> set[str]:
    terms = {term for term in [target.name, _target_symbol(target), *target.aliases] if term}
    return {term for term in terms if term != "unknown"}


def _target_symbol(target: ResolvedEntity | None) -> str:
    if target is None:
        return "unknown"
    symbol = target.identifiers.get("symbol")
    if symbol:
        return symbol
    return target.aliases[0] if target.aliases else "unknown"


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="thesis_draft",
        reason=reason,
        fallback_used=fallback_used,
    )
