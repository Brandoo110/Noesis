from dataclasses import dataclass

from noesis.graph.nodes.thesis_draft import thesis_draft
from noesis.graph.schemas import (
    EvidenceRecord,
    IntelItemDraft,
    ResolvedEntity,
    SentimentTag,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


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


def make_intel() -> IntelItemDraft:
    return IntelItemDraft(
        title="Supplier update",
        content="Supplier pressure eased based on cited evidence.",
        event_type="supply_chain",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.7),
        evidence_ids=["evidence-1"],
    )


def make_entity() -> ResolvedEntity:
    return ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["AAPL", "Apple"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )


def make_mixed_company_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="evidence-2",
        run_id="run-1",
        source="web",
        source_tier=2,
        url="https://example.com/memory",
        title="Micron memory pricing update",
        snippet="Micron memory price hikes may affect Apple device input costs.",
        captured_at=NOW,
    )


def make_mixed_company_intel() -> IntelItemDraft:
    return IntelItemDraft(
        title="Memory pricing pressure",
        content=(
            "Micron and Intel are mentioned in memory market coverage, "
            "with possible cost implications for Apple."
        ),
        event_type="supply_chain",
        source="web",
        source_tier=2,
        url="https://example.com/memory",
        published_at=None,
        sentiment=SentimentTag(dir="neutral", conf=0.7),
        evidence_ids=["evidence-2"],
    )


def make_deps(llm: FakeLLMRouter) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=llm,
        now=lambda: NOW,
    )


class TargetAwareSynthLLM(FakeLLMRouter):
    def available(self, role: LLMRole) -> bool:
        return role == LLMRole.SYNTH

    def complete_json(self, role: LLMRole, prompt: str, schema: type[ThesisDraft]) -> ThesisDraft:
        if "Target entity:" in prompt and "symbol=AAPL" in prompt and "market=US" in prompt:
            return schema.model_validate(
                {
                    "summary": "AAPL faces possible device margin pressure from memory costs.",
                    "assumptions": [
                        {
                            "text": "Apple input costs remain exposed to memory pricing shifts.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-2"],
                        }
                    ],
                }
            )
        return schema.model_validate(
            {
                "summary": "Intel faces demand headwinds from memory cost pressure.",
                "assumptions": [
                    {
                        "text": "Intel remains exposed to PC demand changes.",
                        "kind": "assumption",
                        "evidence_ids": ["evidence-2"],
                    }
                ],
            }
        )


def test_thesis_draft_returns_grounded_draft() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "intel_items": [make_intel()],
        "evidences": [make_evidence()],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "summary": "Evidence suggests supplier pressure is easing.",
                    "assumptions": [
                        {
                            "text": "Supplier pressure remains observable in future filings.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-1"],
                        }
                    ],
                }
            }
        )
    )

    update = thesis_draft(state, deps)

    assert update["thesis_draft"] == ThesisDraft(
        summary="Evidence suggests supplier pressure is easing.",
        assumptions=[
            {
                "text": "Supplier pressure remains observable in future filings.",
                "kind": "assumption",
                "evidence_ids": ["evidence-1"],
            }
        ],
    )


def test_thesis_draft_anchors_summary_to_target_entity() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "resolved_entity": make_entity(),
        "intel_items": [make_mixed_company_intel()],
        "evidences": [make_mixed_company_evidence()],
        "degraded": [],
    }

    update = thesis_draft(state, make_deps(TargetAwareSynthLLM()))

    draft = update["thesis_draft"]
    assert draft is not None
    assert "AAPL" in draft.summary or "Apple" in draft.summary
    assert not draft.summary.startswith("Intel")


def test_thesis_draft_allows_business_words_without_position_advice() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "resolved_entity": make_entity(),
        "intel_items": [make_intel()],
        "evidences": [make_evidence()],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "summary": "Apple approved a buyback program after supplier pressure eased.",
                    "assumptions": [
                        {
                            "text": "Apple capital return remains a business update, not advice.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-1"],
                        }
                    ],
                }
            }
        )
    )

    update = thesis_draft(state, deps)

    draft = update["thesis_draft"]
    assert draft is not None
    assert "buyback" in draft.summary
    assert update["degraded"] == []


def test_thesis_draft_falls_back_when_llm_draft_is_off_target() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "resolved_entity": make_entity(),
        "intel_items": [make_intel()],
        "evidences": [make_evidence()],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "summary": "Intel faces demand headwinds from memory cost pressure.",
                    "assumptions": [
                        {
                            "text": "Apple remains exposed to supplier pressure.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-1"],
                        }
                    ],
                }
            }
        )
    )

    update = thesis_draft(state, deps)

    draft = update["thesis_draft"]
    assert draft is not None
    assert "Apple" in draft.summary
    assert draft.assumptions[0].evidence_ids == ["evidence-1"]
    assert update["degraded"][0].reason == "off_target_thesis"
    assert update["degraded"][0].fallback_used == "safe_rule_based_thesis"


def test_thesis_draft_degrades_when_llm_draft_is_unsafe() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "resolved_entity": make_entity(),
        "intel_items": [make_intel()],
        "evidences": [make_evidence()],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "summary": "Apple is a strong buy after the supplier update.",
                    "assumptions": [
                        {
                            "text": "Investors should buy Apple.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-1"],
                        }
                    ],
                }
            }
        )
    )

    update = thesis_draft(state, deps)

    assert update["thesis_draft"] is None
    assert update["degraded"][0].reason == "invalid_or_unsafe_thesis"
    assert update["degraded"][0].fallback_used == "no_thesis_draft"


def test_thesis_draft_degrades_when_synth_unavailable() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "intel_items": [make_intel()],
        "evidences": [make_evidence()],
        "degraded": [],
    }

    update = thesis_draft(state, make_deps(FakeLLMRouter(available_roles=set())))

    assert update["thesis_draft"] is None
    assert update["degraded"][0].node_name == "thesis_draft"
    assert update["degraded"][0].fallback_used == "no_thesis_draft"


def test_thesis_draft_degrades_when_no_intel_items() -> None:
    state: ResearchState = {
        "position_id": "position-1",
        "resolved_entity": make_entity(),
        "intel_items": [],
        "evidences": [make_mixed_company_evidence()],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "summary": "AAPL faces possible margin pressure from memory costs.",
                    "assumptions": [
                        {
                            "text": "Apple input costs remain exposed to memory pricing shifts.",
                            "kind": "assumption",
                            "evidence_ids": ["evidence-2"],
                        }
                    ],
                }
            }
        )
    )

    update = thesis_draft(state, deps)

    assert update["thesis_draft"] is None
    assert update["degraded"][0].node_name == "thesis_draft"
    assert update["degraded"][0].reason == "no_intel_for_thesis"
    assert update["degraded"][0].fallback_used == "no_thesis_draft"
