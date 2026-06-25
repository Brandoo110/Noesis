from dataclasses import dataclass

from noesis.graph.nodes.thesis_draft import thesis_draft
from noesis.graph.schemas import (
    EvidenceRecord,
    IntelItemDraft,
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


def make_deps(llm: FakeLLMRouter) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=llm,
        now=lambda: NOW,
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
