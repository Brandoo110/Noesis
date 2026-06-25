from dataclasses import dataclass

from noesis.graph.nodes.risk_review import risk_review
from noesis.graph.schemas import (
    EvidenceRecord,
    IntelItemDraft,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


def make_deps() -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="evidence-1",
        run_id="run-1",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        title="Evidence",
        snippet="Supplier pressure eased.",
        captured_at=NOW,
    )


def make_intel(evidence_ids: list[str]) -> IntelItemDraft:
    return IntelItemDraft(
        title="Supplier update",
        content="Supplier pressure eased based on cited evidence.",
        event_type="supply_chain",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.7),
        evidence_ids=evidence_ids,
    )


def test_risk_review_flags_and_removes_ungrounded_intel() -> None:
    state: ResearchState = {
        "evidences": [make_evidence()],
        "intel_items": [make_intel([])],
        "thesis_draft": None,
        "degraded": [],
    }

    update = risk_review(state, make_deps())

    assert update["intel_items"] == []
    assert update["risk_findings"][0].code == "no_evidence_claim"
    assert update["risk_findings"][0].target_ref == "intel:Supplier update"


def test_risk_review_accepts_grounded_intel_and_thesis() -> None:
    assumption = ThesisAssumptionDraft(
        text="Supplier pressure remains observable.",
        kind="assumption",
        evidence_ids=["evidence-1"],
    )
    thesis = ThesisDraft(summary="Evidence-backed thesis.", assumptions=[assumption])
    intel = make_intel(["evidence-1"])
    state: ResearchState = {
        "evidences": [make_evidence()],
        "intel_items": [intel],
        "thesis_draft": thesis,
        "degraded": [],
    }

    update = risk_review(state, make_deps())

    assert update["risk_findings"] == []
    assert update["intel_items"] == [intel]
    assert update["thesis_draft"] == thesis


def test_risk_review_blocks_investment_redline_language() -> None:
    assumption = ThesisAssumptionDraft(
        text="Supplier pressure remains observable.",
        kind="assumption",
        evidence_ids=["evidence-1"],
    )
    thesis = ThesisDraft(summary="Buy this stock at a higher target price.", assumptions=[assumption])
    state: ResearchState = {
        "evidences": [make_evidence()],
        "intel_items": [make_intel(["evidence-1"])],
        "thesis_draft": thesis,
        "degraded": [],
    }

    update = risk_review(state, make_deps())

    assert update["thesis_draft"] is None
    assert update["risk_findings"][0].code == "bad_basis"
    assert update["risk_findings"][0].target_ref == "thesis:redline"
