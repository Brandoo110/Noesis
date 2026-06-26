from noesis.graph.grounding import (
    check_edge_basis,
    check_investment_redlines,
    check_intel,
    check_thesis,
    filter_valid_edges,
)
from noesis.graph.schemas import (
    EvidenceRecord,
    GraphEdgeDraft,
    IntelItemDraft,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)


NOW = "2026-06-26T00:00:00Z"


def make_evidence(id: str = "evidence-1") -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        run_id="run-1",
        source="web",
        source_tier=2,
        url=f"https://example.com/{id}",
        title="Evidence",
        snippet="Evidence snippet.",
        captured_at=NOW,
    )


def make_intel(evidence_ids: list[str]) -> IntelItemDraft:
    return IntelItemDraft(
        title="Intel",
        content="Evidence-backed content.",
        event_type="news",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.7),
        evidence_ids=evidence_ids,
    )


def make_edge(
    *,
    basis: str = "source_backed",
    evidence_ids: list[str] | None = None,
    confidence: float = 0.8,
) -> GraphEdgeDraft:
    return GraphEdgeDraft(
        to_name="TSMC",
        to_symbol="TSM",
        to_node_type="company",
        relation="supplier",
        basis=basis,
        confidence=confidence,
        evidence_ids=["evidence-1"] if evidence_ids is None else evidence_ids,
        rationale="TSMC is cited as a supplier.",
    )


def test_check_intel_flags_empty_and_fabricated_evidence_ids() -> None:
    evidences = [make_evidence()]

    findings = check_intel(
        [make_intel([]), make_intel(["missing-evidence"])],
        evidences,
    )

    assert [finding.code for finding in findings] == [
        "no_evidence_claim",
        "no_evidence_claim",
    ]


def test_check_thesis_flags_ungrounded_assumption() -> None:
    thesis = ThesisDraft(
        summary="Evidence-backed thesis.",
        assumptions=[
            ThesisAssumptionDraft(
                text="Ungrounded assumption.",
                kind="assumption",
                evidence_ids=[],
            )
        ],
    )

    findings = check_thesis(thesis, [make_evidence()])

    assert [finding.code for finding in findings] == [
        "no_evidence_claim",
        "thesis_no_assumption_evidence",
    ]


def test_check_investment_redlines_matches_english_and_chinese_terms() -> None:
    english = ThesisDraft(
        summary="This has a target price.",
        assumptions=[
            ThesisAssumptionDraft(
                text="Evidence-backed assumption.",
                kind="assumption",
                evidence_ids=["evidence-1"],
            )
        ],
    )
    chinese = ThesisDraft(
        summary="证据摘要。",
        assumptions=[
            ThesisAssumptionDraft(
                text="建议买入。",
                kind="assumption",
                evidence_ids=["evidence-1"],
            )
        ],
    )

    assert check_investment_redlines(english)[0].code == "bad_basis"
    assert check_investment_redlines(chinese)[0].target_ref == "thesis:redline"


def test_check_edge_basis_flags_source_backed_without_valid_evidence() -> None:
    evidences = [make_evidence("evidence-1")]

    findings = check_edge_basis(
        [
            make_edge(evidence_ids=[]),
            make_edge(evidence_ids=["missing-evidence"]),
        ],
        evidences,
    )

    assert [finding.code for finding in findings] == [
        "source_backed_empty",
        "source_backed_empty",
    ]


def test_check_edge_basis_allows_inferred_edges_with_confidence() -> None:
    edge = make_edge(basis="inferred", evidence_ids=[], confidence=0.55)

    assert check_edge_basis([edge], [make_evidence()]) == []
    assert edge.confidence == 0.55


def test_filter_valid_edges_drops_invalid_source_backed_edges() -> None:
    valid = make_edge(evidence_ids=["evidence-1"])
    invalid = make_edge(evidence_ids=[])
    inferred = make_edge(basis="inferred", evidence_ids=[], confidence=0.6)

    assert filter_valid_edges(
        [valid, invalid, inferred],
        [make_evidence("evidence-1")],
    ) == [valid, inferred]
