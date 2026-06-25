from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.schemas import DegradeNote, EvidenceRecord, IntelItemDraft, ThesisDraft
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("position_id", "intel_items", "evidences")
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
    if not deps.llm.available(LLMRole.SYNTH):
        degraded.append(_degrade("synth_llm_unavailable", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    try:
        draft = deps.llm.complete_json(
            LLMRole.SYNTH,
            _prompt(state.get("intel_items", []), state.get("evidences", [])),
            ThesisDraft,
        )
    except (LLMUnavailableError, ResearchNodeError) as exc:
        degraded.append(_degrade(exc.reason or "llm_failed", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    valid_ids = {item.id for item in state.get("evidences", [])}
    if not _valid_draft(draft, valid_ids):
        degraded.append(_degrade("invalid_or_unsafe_thesis", "no_thesis_draft"))
        return {"thesis_draft": None, "degraded": degraded}
    return {"thesis_draft": draft, "degraded": degraded}


def _prompt(intel_items: list[IntelItemDraft], evidences: list[EvidenceRecord]) -> str:
    intel_text = "\n".join(f"- {item.title}: {item.content}" for item in intel_items)
    evidence_text = "\n".join(f"- {item.id}: {item.snippet}" for item in evidences)
    return (
        "Draft a research thesis for confirmation. Do not recommend buying, "
        "selling, trading, price targets, or stock-price predictions. "
        "Every assumption must cite provided evidence ids.\n"
        f"Intel:\n{intel_text}\nEvidence:\n{evidence_text}"
    )


def _valid_draft(draft: ThesisDraft, valid_ids: set[str]) -> bool:
    if _has_redline_text(draft.summary) or not draft.assumptions:
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


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="thesis_draft",
        reason=reason,
        fallback_used=fallback_used,
    )
