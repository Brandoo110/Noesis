import pytest

from noesis.eval.metrics import evaluate_run
from noesis.graph.schemas import (
    EvidenceRecord,
    GraphEdgeDraft,
    IntelItemDraft,
    ResolvedEntity,
    SentimentTag,
    ThesisAssumptionDraft,
    ThesisDraft,
)

NOW = "2026-06-28T00:00:00Z"


def test_evaluate_run_returns_perfect_scores_for_grounded_output() -> None:
    metrics = evaluate_run(
        [make_intel("Apple supplier update", ["evidence-1"])],
        make_thesis(summary="Apple evidence-backed thesis."),
        [make_edge(evidence_ids=["evidence-1"])],
        [make_evidence("evidence-1")],
        make_target(),
    )

    assert metrics == {
        "grounding_rate": 1.0,
        "redline_compliance": 1.0,
        "basis_honesty": 1.0,
        "anchor_rate": 1.0,
    }


def test_evaluate_run_lowers_grounding_rate_for_ungrounded_intel() -> None:
    metrics = evaluate_run(
        [
            make_intel("Apple supplier update", ["evidence-1"]),
            make_intel("Apple unsupported update", []),
        ],
        make_thesis(summary="Apple evidence-backed thesis."),
        [make_edge(evidence_ids=["evidence-1"])],
        [make_evidence("evidence-1")],
        make_target(),
    )

    assert metrics["grounding_rate"] == pytest.approx(2 / 3)


def test_evaluate_run_flags_redline_thesis() -> None:
    metrics = evaluate_run(
        [make_intel("Apple supplier update", ["evidence-1"])],
        make_thesis(summary="Apple price target $250."),
        [make_edge(evidence_ids=["evidence-1"])],
        [make_evidence("evidence-1")],
        make_target(),
    )

    assert metrics["redline_compliance"] == 0.0


def test_evaluate_run_lowers_anchor_rate_when_intel_omits_target() -> None:
    metrics = evaluate_run(
        [
            make_intel("Apple supplier update", ["evidence-1"]),
            make_intel("Unrelated supplier update", ["evidence-1"]),
        ],
        make_thesis(summary="Apple evidence-backed thesis."),
        [make_edge(evidence_ids=["evidence-1"])],
        [make_evidence("evidence-1")],
        make_target(),
    )

    assert metrics["anchor_rate"] == 0.5


def test_evaluate_run_empty_inputs_do_not_crash_and_use_neutral_defaults() -> None:
    metrics = evaluate_run([], None, [], [], make_target())

    assert metrics == {
        "grounding_rate": 1.0,
        "redline_compliance": 1.0,
        "basis_honesty": 1.0,
        "anchor_rate": 1.0,
    }


def make_evidence(id: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        run_id="run-1",
        source="web",
        source_tier=2,
        url=f"https://example.com/{id}",
        title="Evidence",
        snippet="Apple evidence snippet.",
        captured_at=NOW,
    )


def make_intel(title: str, evidence_ids: list[str]) -> IntelItemDraft:
    return IntelItemDraft(
        title=title,
        content=f"{title} content.",
        event_type="news",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.8),
        evidence_ids=evidence_ids,
    )


def make_thesis(summary: str) -> ThesisDraft:
    return ThesisDraft(
        summary=summary,
        assumptions=[
            ThesisAssumptionDraft(
                text="Apple assumption with evidence.",
                kind="assumption",
                evidence_ids=["evidence-1"],
            )
        ],
    )


def make_edge(evidence_ids: list[str]) -> GraphEdgeDraft:
    return GraphEdgeDraft(
        to_name="TSMC",
        to_symbol="TSM",
        to_node_type="company",
        relation="supplier",
        basis="source_backed",
        confidence=0.8,
        evidence_ids=evidence_ids,
        rationale="Evidence-backed supplier edge.",
    )


def make_target() -> ResolvedEntity:
    return ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["Apple"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )
