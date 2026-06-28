from collections.abc import Sequence
from typing import TypedDict

from noesis.graph.grounding import (
    check_edge_basis,
    check_intel,
    check_investment_redlines,
    check_thesis,
)
from noesis.graph.schemas import (
    EvidenceRecord,
    GraphEdgeDraft,
    IntelItemDraft,
    ResolvedEntity,
    ThesisDraft,
)


class EvalMetrics(TypedDict):
    grounding_rate: float
    redline_compliance: float
    basis_honesty: float
    anchor_rate: float


def evaluate_run(
    intel_items: Sequence[IntelItemDraft],
    thesis: ThesisDraft | None,
    edges: Sequence[GraphEdgeDraft],
    evidences: Sequence[EvidenceRecord],
    target: ResolvedEntity,
) -> EvalMetrics:
    evidence_list = list(evidences)
    intel_list = list(intel_items)
    edge_list = list(edges)
    return {
        "grounding_rate": _grounding_rate(intel_list, thesis, evidence_list),
        "redline_compliance": _redline_compliance(thesis),
        "basis_honesty": _basis_honesty(edge_list, evidence_list),
        "anchor_rate": _anchor_rate(intel_list, target),
    }


def _grounding_rate(
    intel_items: list[IntelItemDraft],
    thesis: ThesisDraft | None,
    evidences: list[EvidenceRecord],
) -> float:
    assumption_count = len(thesis.assumptions) if thesis is not None else 0
    total = len(intel_items) + assumption_count
    if total == 0:
        return 1.0
    intel_findings = check_intel(intel_items, evidences)
    thesis_findings = check_thesis(thesis, evidences)
    invalid_intel = len({finding.target_ref for finding in intel_findings})
    invalid_assumptions = len(
        {
            finding.target_ref
            for finding in thesis_findings
            if finding.target_ref.startswith("thesis_assumption:")
        }
    )
    return _ratio(total - invalid_intel - invalid_assumptions, total)


def _redline_compliance(thesis: ThesisDraft | None) -> float:
    return 0.0 if check_investment_redlines(thesis) else 1.0


def _basis_honesty(
    edges: list[GraphEdgeDraft], evidences: list[EvidenceRecord]
) -> float:
    source_backed = [edge for edge in edges if edge.basis == "source_backed"]
    if not source_backed:
        return 1.0
    findings = check_edge_basis(source_backed, evidences)
    return _ratio(len(source_backed) - len(findings), len(source_backed))


def _anchor_rate(items: list[IntelItemDraft], target: ResolvedEntity) -> float:
    if not items:
        return 1.0
    terms = _target_terms(target)
    if not terms:
        return 1.0
    anchored = sum(1 for item in items if _contains_any(_intel_text(item), terms))
    return _ratio(anchored, len(items))


def _target_terms(target: ResolvedEntity) -> set[str]:
    return {term.lower() for term in [target.name, *target.aliases] if term.strip()}


def _intel_text(item: IntelItemDraft) -> str:
    return f"{item.title} {item.content}".lower()


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return max(0.0, min(1.0, numerator / denominator))
