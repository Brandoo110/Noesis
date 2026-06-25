from dataclasses import dataclass

from noesis.graph.nodes.intel_synth import intel_synth
from noesis.graph.schemas import EvidenceRecord, IntelItemDraft, SentimentTag
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


def make_evidence(id: str = "evidence-1") -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        run_id="run-1",
        source="web",
        source_tier=2,
        url=f"https://example.com/{id}",
        title="Evidence",
        snippet="Supplier pressure eased.",
        captured_at=NOW,
    )


def make_deps(llm: FakeLLMRouter) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=llm,
        now=lambda: NOW,
    )


def make_item(evidence_ids: list[str], title: str = "Supplier update") -> dict[str, object]:
    return {
        "title": title,
        "content": "Supplier pressure eased based on cited evidence.",
        "event_type": "supply_chain",
        "source": "web",
        "source_tier": 2,
        "url": "https://example.com/evidence-1",
        "published_at": None,
        "sentiment": {"dir": "neutral", "conf": 0.7},
        "evidence_ids": evidence_ids,
    }


def test_intel_synth_returns_grounded_intel_items() -> None:
    state: ResearchState = {
        "entity_id": "entity-1",
        "evidences": [make_evidence("evidence-1"), make_evidence("evidence-2")],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.LIGHT: {
                    "items": [
                        make_item(["evidence-1"], "Supplier update"),
                        make_item(["evidence-2"], "Demand update"),
                    ]
                }
            }
        )
    )

    update = intel_synth(state, deps)

    assert len(update["intel_items"]) == 2
    assert update["intel_items"][0] == IntelItemDraft(
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


def test_intel_synth_drops_items_with_unknown_evidence_ids() -> None:
    state: ResearchState = {
        "entity_id": "entity-1",
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.LIGHT: {
                    "items": [
                        make_item(["evidence-1"], "Grounded"),
                        make_item(["missing-evidence"], "Ungrounded"),
                    ]
                }
            }
        )
    )

    update = intel_synth(state, deps)

    assert [item.title for item in update["intel_items"]] == ["Grounded"]
    assert update["degraded"][0].fallback_used == "drop_invalid_intel"


def test_intel_synth_degrades_when_light_llm_unavailable() -> None:
    state: ResearchState = {
        "entity_id": "entity-1",
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    update = intel_synth(state, make_deps(FakeLLMRouter(available_roles=set())))

    assert update["intel_items"] == []
    assert update["degraded"][0].node_name == "intel_synth"
    assert update["degraded"][0].fallback_used == "empty_intel_items"
