from dataclasses import dataclass
from pathlib import Path

from noesis.db.models import EntityRow
from noesis.graph.nodes.intel_synth import REQUIRED_STATE_KEYS, intel_synth
from noesis.graph.schemas import (
    EvidenceRecord,
    IntelItemDraft,
    ResolvedEntity,
    SentimentTag,
)
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


@dataclass
class EntitiesOnlyRepos:
    entities: "FakeEntitiesRepo"


@dataclass
class FakeEntitiesRepo:
    row: EntityRow | None

    def get(self, id: str) -> EntityRow | None:
        return self.row if self.row is not None and self.row.id == id else None


class CapturingLightLLM(FakeLLMRouter):
    def __init__(self) -> None:
        super().__init__(json_by_role={LLMRole.LIGHT: {"items": [make_item(["evidence-1"])]}})
        self.last_prompt: str | None = None

    def complete_json(self, role: LLMRole, prompt: str, schema: type) -> object:
        self.last_prompt = prompt
        return super().complete_json(role, prompt, schema)


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


def make_deps_with_entities(llm: FakeLLMRouter, row: EntityRow | None) -> GraphDeps:
    return GraphDeps(
        repos=EntitiesOnlyRepos(FakeEntitiesRepo(row)),
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


def make_entity() -> ResolvedEntity:
    return ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["Apple", "AAPL"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )


def make_entity_row() -> EntityRow:
    return EntityRow(
        id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases_json='["Apple", "AAPL"]',
        identifiers_json='{"symbol": "AAPL"}',
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def test_intel_synth_prompt_anchors_to_resolved_entity() -> None:
    llm = CapturingLightLLM()
    prompt_file = Path("prompts/intel_synth.md").read_text(encoding="utf-8")
    state: ResearchState = {
        "entity_id": "entity-aapl",
        "resolved_entity": make_entity(),
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    intel_synth(state, make_deps(llm))

    assert "resolved_entity" in REQUIRED_STATE_KEYS
    assert llm.last_prompt is not None
    assert "Apple Inc." in llm.last_prompt
    assert "AAPL" in llm.last_prompt
    assert "PRIMARY SUBJECT" in llm.last_prompt
    assert "DISCARD" in llm.last_prompt
    for text in (llm.last_prompt, prompt_file):
        assert "简体中文" in text
        assert "原始英文证据" in text


def test_intel_synth_uses_entity_repo_as_target_fallback() -> None:
    llm = CapturingLightLLM()
    state: ResearchState = {
        "entity_id": "entity-aapl",
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    update = intel_synth(state, make_deps_with_entities(llm, make_entity_row()))

    assert update["intel_items"][0].title == "Supplier update"
    assert llm.last_prompt is not None
    assert "Apple Inc." in llm.last_prompt
    assert "AAPL" in llm.last_prompt
    assert not update["degraded"]


def test_intel_synth_degrades_when_target_unresolved() -> None:
    llm = CapturingLightLLM()
    state: ResearchState = {
        "entity_id": "missing-entity",
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    update = intel_synth(state, make_deps_with_entities(llm, None))

    assert update["intel_items"][0].title == "Supplier update"
    assert update["degraded"][0].reason == "target_unresolved"
    assert update["degraded"][0].fallback_used == "unanchored_intel_prompt"


def test_intel_synth_returns_grounded_intel_items() -> None:
    state: ResearchState = {
        "entity_id": "entity-1",
        "resolved_entity": make_entity(),
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
        "resolved_entity": make_entity(),
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
        "resolved_entity": make_entity(),
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    update = intel_synth(state, make_deps(FakeLLMRouter(available_roles=set())))

    assert update["intel_items"] == []
    assert update["degraded"][0].node_name == "intel_synth"
    assert update["degraded"][0].fallback_used == "empty_intel_items"
