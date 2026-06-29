from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.grounding import check_investment_redlines
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
    invalid_reason = _invalid_draft_reason(draft, valid_ids, state.get("resolved_entity"))
    if invalid_reason is not None:
        fallback = _fallback_draft(
            state.get("resolved_entity"),
            intel_items,
            valid_ids,
        )
        if invalid_reason == "off_target_thesis" and fallback is not None and _valid_draft(
            fallback,
            valid_ids,
            state.get("resolved_entity"),
        ):
            degraded.append(
                _degrade("off_target_thesis", "safe_rule_based_thesis")
            )
            return {"thesis_draft": fallback, "degraded": degraded}
        degraded.append(_degrade(invalid_reason, "no_thesis_draft"))
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
    return _invalid_draft_reason(draft, valid_ids, target) is None


def _invalid_draft_reason(
    draft: ThesisDraft,
    valid_ids: set[str],
    target: ResolvedEntity | None,
) -> str | None:
    if check_investment_redlines(draft) or not draft.assumptions:
        return "invalid_or_unsafe_thesis"
    for assumption in draft.assumptions:
        if not assumption.evidence_ids or not set(assumption.evidence_ids).issubset(valid_ids):
            return "invalid_or_unsafe_thesis"
    if target is not None and not _mentions_target(draft.summary, target):
        return "off_target_thesis"
    return None


def _fallback_draft(
    target: ResolvedEntity | None,
    intel_items: list[IntelItemDraft],
    valid_ids: set[str],
) -> ThesisDraft | None:
    label = _target_label(target)
    for item in intel_items:
        evidence_ids = [
            evidence_id for evidence_id in item.evidence_ids if evidence_id in valid_ids
        ]
        if not evidence_ids:
            continue
        return ThesisDraft(
            summary=(
                f"{label} has evidence-backed developments that require "
                "confirmation before forming a research view."
            ),
            assumptions=[
                {
                    "text": (
                        f"{label} remains linked to the cited development; "
                        "the implication should be reviewed against the evidence."
                    ),
                    "kind": "assumption",
                    "evidence_ids": evidence_ids,
                }
            ],
        )
    return None


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


def _target_label(target: ResolvedEntity | None) -> str:
    if target is None:
        return "The target entity"
    symbol = _target_symbol(target)
    if target.name:
        return target.name
    if symbol != "unknown":
        return symbol
    return "The target entity"


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="thesis_draft",
        reason=reason,
        fallback_used=fallback_used,
    )
