import re

from noesis.graph.schemas import (
    EvidenceRecord,
    GraphEdgeDraft,
    IntelItemDraft,
    RiskFinding,
    ThesisDraft,
)

INVESTMENT_REDLINE_TERMS = (
    "buy",
    "sell",
    "price target",
    "target price",
    "overweight",
    "underweight",
    "strong buy",
    "reduce position",
    "reduce holdings",
    "accumulate shares",
    "rated outperform",
    "rated underperform",
    "predict stock price",
    "买入",
    "卖出",
    "目标价",
    "预测股价",
)


def check_intel(
    items: list[IntelItemDraft], evidences: list[EvidenceRecord]
) -> list[RiskFinding]:
    valid_ids = {item.id for item in evidences}
    findings: list[RiskFinding] = []
    for item in items:
        if not item.evidence_ids or not set(item.evidence_ids).issubset(valid_ids):
            findings.append(
                RiskFinding(
                    code="no_evidence_claim",
                    target_ref=f"intel:{item.title}",
                    detail="Intel item has no valid evidence ids.",
                )
            )
    return findings


def filter_grounded_intel(
    items: list[IntelItemDraft], evidences: list[EvidenceRecord]
) -> list[IntelItemDraft]:
    valid_ids = {item.id for item in evidences}
    return [
        item
        for item in items
        if item.evidence_ids and set(item.evidence_ids).issubset(valid_ids)
    ]


def check_edge_basis(
    edges: list[GraphEdgeDraft], evidences: list[EvidenceRecord]
) -> list[RiskFinding]:
    valid_ids = {item.id for item in evidences}
    findings: list[RiskFinding] = []
    for index, edge in enumerate(edges):
        if edge.basis == "source_backed":
            if not edge.evidence_ids or not set(edge.evidence_ids).issubset(valid_ids):
                findings.append(_edge_finding(index, edge, "source_backed_empty"))
        elif edge.confidence is None:
            findings.append(_edge_finding(index, edge, "bad_basis"))
    return findings


def filter_valid_edges(
    edges: list[GraphEdgeDraft], evidences: list[EvidenceRecord]
) -> list[GraphEdgeDraft]:
    invalid_refs = {finding.target_ref for finding in check_edge_basis(edges, evidences)}
    return [
        edge
        for index, edge in enumerate(edges)
        if _edge_ref(index, edge) not in invalid_refs
    ]


def check_thesis(
    draft: ThesisDraft | None, evidences: list[EvidenceRecord]
) -> list[RiskFinding]:
    if draft is None:
        return []
    valid_ids = {item.id for item in evidences}
    findings: list[RiskFinding] = []
    grounded_assumptions = 0
    for index, assumption in enumerate(draft.assumptions):
        if assumption.evidence_ids and set(assumption.evidence_ids).issubset(valid_ids):
            grounded_assumptions += 1
            continue
        findings.append(
            RiskFinding(
                code="no_evidence_claim",
                target_ref=f"thesis_assumption:{index}",
                detail="Thesis assumption has no valid evidence ids.",
            )
        )
    if grounded_assumptions == 0:
        findings.append(
            RiskFinding(
                code="thesis_no_assumption_evidence",
                target_ref="thesis",
                detail="Thesis has no evidence-backed assumptions.",
            )
        )
    return findings


def check_investment_redlines(draft: ThesisDraft | None) -> list[RiskFinding]:
    if draft is None:
        return []
    texts = [draft.summary, *[assumption.text for assumption in draft.assumptions]]
    if any(_contains_redline(text) for text in texts):
        return [
            RiskFinding(
                code="bad_basis",
                target_ref="thesis:redline",
                detail="Thesis contains buy/sell, target-price, or prediction language.",
            )
        ]
    return []


def thesis_is_grounded(
    draft: ThesisDraft | None, evidences: list[EvidenceRecord]
) -> bool:
    return not check_thesis(draft, evidences)


def _contains_redline(text: str) -> bool:
    lowered = text.lower()
    return any(_term_matches(lowered, term) for term in INVESTMENT_REDLINE_TERMS)


def _term_matches(lowered_text: str, term: str) -> bool:
    if any("\u4e00" <= char <= "\u9fff" for char in term):
        return term in lowered_text
    return re.search(rf"\b{re.escape(term)}\b", lowered_text) is not None


def _edge_finding(index: int, edge: GraphEdgeDraft, code: str) -> RiskFinding:
    return RiskFinding(
        code=code,
        target_ref=_edge_ref(index, edge),
        detail="Graph edge basis is not backed by valid evidence.",
    )


def _edge_ref(index: int, edge: GraphEdgeDraft) -> str:
    return f"graph_edge:{index}:{edge.to_name}"
