from typing import Any, is_typeddict

from noesis.graph.schemas import (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    IngestedDoc,
    IntelItemDraft,
    PositionInput,
    ResolvedEntity,
    RiskFinding,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, RepoBundle, ResearchState, ResearchStateUpdate


def test_graph_schemas_can_be_instantiated() -> None:
    position = PositionInput(symbol="AAPL", market="US")
    entity = ResolvedEntity(
        entity_id="entity-1",
        node_type="company",
        name="Apple Inc.",
        identifiers={"symbol": "AAPL"},
        market="US",
    )
    doc = IngestedDoc(
        source="web",
        source_tier=2,
        title="Apple supplier update",
        url="https://example.com/apple",
        text="Apple supplier update text.",
    )
    evidence = EvidenceRecord(
        id="evidence-1",
        run_id="run-1",
        source="web",
        source_tier=2,
        url="https://example.com/apple",
        title="Apple supplier update",
        snippet="Supplier update",
        captured_at="2026-06-26T00:00:00Z",
    )
    sentiment = SentimentTag(dir="neutral", conf=0.75)
    intel = IntelItemDraft(
        title="Supplier update",
        content="Apple supplier update.",
        event_type="supply_chain",
        source="web",
        source_tier=2,
        url="https://example.com/apple",
        published_at=None,
        sentiment=sentiment,
        evidence_ids=["evidence-1"],
    )
    assumption = ThesisAssumptionDraft(
        text="Supplier concentration remains a risk.",
        kind="risk",
        evidence_ids=["evidence-1"],
    )
    thesis = ThesisDraft(summary="Evidence-backed draft.", assumptions=[assumption])
    finding = RiskFinding(
        code="no_evidence_claim",
        target_ref="intel:1",
        detail="Missing evidence.",
    )
    degrade = DegradeNote(
        node_name="ingest",
        reason="search unavailable",
        fallback_used="empty_docs",
    )
    confirmation = ConfirmationResult(status="edited", edited_assumptions=[assumption])

    assert position.kind == "owned"
    assert entity.identifiers["symbol"] == "AAPL"
    assert doc.published_at is None
    assert evidence.run_id == "run-1"
    assert evidence.published_at is None
    assert intel.sentiment == sentiment
    assert thesis.assumptions == [assumption]
    assert finding.code == "no_evidence_claim"
    assert degrade.fallback_used == "empty_docs"
    assert confirmation.edited_assumptions == [assumption]


def test_intel_item_draft_allows_empty_evidence_ids() -> None:
    intel = IntelItemDraft(
        title="Ungrounded draft",
        content="Grounding catches this later.",
        event_type="news",
        source="fake",
        source_tier=4,
        url=None,
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.1),
        evidence_ids=[],
    )

    assert intel.evidence_ids == []


def test_research_state_contract_is_total_false_typed_dict() -> None:
    state: ResearchState = {
        "run_id": "run-1",
        "node_kind": "seed",
        "intel_items": [],
        "degraded": [],
    }

    assert is_typeddict(ResearchState)
    assert ResearchState.__total__ is False
    assert state["node_kind"] == "seed"
    assert ResearchStateUpdate == dict[str, Any]


def test_graph_deps_can_hold_repo_bundle_and_adapters() -> None:
    bundle = RepoBundle(
        positions=object(),
        entities=object(),
        runs=object(),
        traces=object(),
        evidences=object(),
        intel=object(),
        theses=object(),
        assumptions=object(),
        approvals=object(),
    )
    deps = GraphDeps(
        repos=bundle,
        search=object(),
        retriever=object(),
        llm=object(),
        now=lambda: "2026-06-26T00:00:00Z",
    )

    assert deps.repos is bundle
    assert deps.now() == "2026-06-26T00:00:00Z"
