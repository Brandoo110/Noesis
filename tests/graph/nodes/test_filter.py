from dataclasses import dataclass

from noesis.graph.nodes.filter import filter as filter_node
from noesis.graph.schemas import IngestedDoc
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


def test_filter_returns_empty_for_empty_docs() -> None:
    state: ResearchState = {"ingested_docs": [], "degraded": []}

    update = filter_node(state, make_deps())

    assert update["filtered_docs"] == []
    assert update["degraded"] == []


def test_filter_removes_docs_without_text() -> None:
    good = IngestedDoc(
        source="web",
        source_tier=2,
        title="Useful",
        url="https://example.com/good",
        text="Relevant text.",
    )
    empty = IngestedDoc(
        source="web",
        source_tier=2,
        title="Empty",
        url="https://example.com/empty",
        text="   ",
    )
    state: ResearchState = {"ingested_docs": [good, empty], "degraded": []}

    update = filter_node(state, make_deps())

    assert update["filtered_docs"] == [good]
