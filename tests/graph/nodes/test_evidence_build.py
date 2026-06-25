from dataclasses import dataclass, field

from noesis.graph.nodes.evidence_build import evidence_build
from noesis.graph.schemas import EvidenceRecord, IngestedDoc
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


@dataclass
class FakeRetriever:
    indexed: list[EvidenceRecord] = field(default_factory=list)

    def index(self, evidences: list[EvidenceRecord]) -> None:
        self.indexed.extend(evidences)


class FailingRetriever:
    def index(self, evidences: list[EvidenceRecord]) -> None:
        raise RuntimeError("vector store unavailable")


def make_doc(url: str | None, text: str, title: str = "Doc") -> IngestedDoc:
    return IngestedDoc(
        source="web",
        source_tier=2,
        title=title,
        url=url,
        text=text,
        published_at=None,
    )


def make_deps(retriever: object) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=retriever,
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def test_evidence_build_deduplicates_and_indexes_evidence() -> None:
    retriever = FakeRetriever()
    state: ResearchState = {
        "run_id": "run-1",
        "entity_id": "entity-1",
        "filtered_docs": [
            make_doc("https://example.com/a", "Apple supplier update."),
            make_doc("https://example.com/a", "Duplicate by URL."),
            make_doc("https://example.com/b", "Battery pressure eases."),
        ],
        "degraded": [],
    }

    update = evidence_build(state, make_deps(retriever))

    evidences = update["evidences"]
    assert len(evidences) == 2
    assert [item.run_id for item in evidences] == ["run-1", "run-1"]
    assert all(item.id.startswith("evidence-") for item in evidences)
    assert retriever.indexed == evidences


def test_evidence_build_degrades_when_indexing_fails() -> None:
    state: ResearchState = {
        "run_id": "run-1",
        "entity_id": "entity-1",
        "filtered_docs": [make_doc("https://example.com/a", "Apple supplier update.")],
        "degraded": [],
    }

    update = evidence_build(state, make_deps(FailingRetriever()))

    assert len(update["evidences"]) == 1
    assert update["degraded"][0].node_name == "evidence_build"
    assert update["degraded"][0].fallback_used == "evidence_without_vector_index"
