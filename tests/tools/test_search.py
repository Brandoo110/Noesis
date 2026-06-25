import pytest

from noesis.graph.errors import IngestError
from noesis.graph.schemas import IngestedDoc
from noesis.tools.search.base import SearchAdapter
from noesis.tools.search.fake import FakeSearchAdapter
from noesis.tools.search.tavily import TavilySearchAdapter


def test_fake_search_adapter_returns_configured_docs() -> None:
    docs = [
        IngestedDoc(
            source="fake",
            source_tier=3,
            title="First",
            url="https://example.com/1",
            text="first text",
        ),
        IngestedDoc(
            source="fake",
            source_tier=3,
            title="Second",
            url="https://example.com/2",
            text="second text",
        ),
    ]
    adapter: SearchAdapter = FakeSearchAdapter(docs)

    result = adapter.search("Apple", limit=1)

    assert result == docs[:1]


def test_tavily_adapter_without_key_raises_ingest_error() -> None:
    adapter = TavilySearchAdapter(api_key="")

    with pytest.raises(IngestError):
        adapter.search("Apple", limit=2)
