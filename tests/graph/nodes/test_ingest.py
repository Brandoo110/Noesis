from dataclasses import dataclass

from noesis.graph.errors import IngestError
from noesis.graph.nodes.ingest import ingest
from noesis.graph.schemas import IngestedDoc, ResolvedEntity
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.search.fake import FakeSearchAdapter


NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


class FailingSearchAdapter:
    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        raise IngestError("search unavailable", reason="search_failed")


class CapturingSearchAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        self.queries.append(query)
        return []


def make_entity() -> ResolvedEntity:
    return ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["AAPL"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )


def make_deps(search: object) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=search,
        retriever=object(),
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def test_ingest_returns_search_documents() -> None:
    docs = [
        IngestedDoc(
            source="web",
            source_tier=2,
            title="Apple supplier",
            url="https://example.com/1",
            text="Supplier update.",
        ),
        IngestedDoc(
            source="web",
            source_tier=3,
            title="Apple demand",
            url="https://example.com/2",
            text="Demand update.",
        ),
    ]
    state: ResearchState = {"resolved_entity": make_entity(), "degraded": []}

    update = ingest(state, make_deps(FakeSearchAdapter(docs)))

    assert update["ingested_docs"] == docs
    assert update["degraded"] == []


def test_ingest_uses_finance_oriented_recent_query() -> None:
    search = CapturingSearchAdapter()
    state: ResearchState = {"resolved_entity": make_entity(), "degraded": []}

    ingest(state, make_deps(search))

    assert search.queries
    query = search.queries[0].lower()
    assert "aapl" in query
    assert "stock" in query
    assert "latest news" in query
    assert "earnings" in query
    assert "results" in query


def test_ingest_degrades_to_empty_docs_when_search_fails() -> None:
    state: ResearchState = {"resolved_entity": make_entity(), "degraded": []}

    update = ingest(state, make_deps(FailingSearchAdapter()))

    assert update["ingested_docs"] == []
    assert update["degraded"][0].node_name == "ingest"
    assert update["degraded"][0].fallback_used == "empty_docs"
